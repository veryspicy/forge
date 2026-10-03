import { localStg } from '@/utils/storage';

/**
 * 主线程停转（页面冻结）观测器
 *
 * 背景：admin 曾出现 login/me 返回 200 之后页面零响应、连 30s 自检请求也停发的现象，
 * 特征指向主线程级停转（渲染进程冻结）。冻结期间浏览器控制台不可用、刷新后现场即丢失，
 * 因此本模块把观测数据落到持久化缓冲，使"刷新后仍可回溯冻结前的最后阶段与停摆时长"。
 *
 * 观测通道：
 * 1. 心跳：每 2s 写一次 sessionStorage（附带当前阶段），冻结期间心跳停写，用陈旧度反推停摆时长
 * 2. 阻塞自检：页面可见时心跳定时器实际延迟超过阈值 → 判定主线程被阻塞过，记录阻塞时长
 * 3. 阶段打点：markPhase() 记录关键链路阶段与时刻（登录、路由过渡、请求 pending/done、自检、刷新决策）
 * 4. 长任务：PerformanceObserver 统计长任务（次数 / 最长 / 发生时刻 / 当时阶段）
 * 5. 结构化报告：环形缓冲写 localStorage，window.__forgeStallReports() 读取，window.__forgeStallDump() 打印
 *
 * 约束：只记录布尔与数字，禁止记录 token 等凭据；存储不可用（隐私模式 / 配额）时静默降级到内存。
 */

/** 心跳 key：sessionStorage，随标签页生命周期，用于跨刷新判定上一会话是否停摆 */
const HB_KEY = 'forge:stall-hb';

/** 结构化报告环形缓冲 key：localStorage，跨刷新保留 */
const REPORT_KEY = 'forge:stall-reports';

/** 心跳间隔(ms) */
const HEARTBEAT_INTERVAL = 2_000;

/** 心跳陈旧阈值(ms)：正常心跳间隔 2s，超过该值说明上一会话心跳停摆 */
const STALE_THRESHOLD = 8_000;

/** 上一会话心跳过期上限(ms)：超过则视为废弃标签页，不再判定为冻结 */
const STALE_MAX_GAP = 30 * 60 * 1000;

/** 阻塞判定阈值(ms)：页面可见时心跳定时器被推迟超过该值即判定主线程阻塞 */
const BLOCK_THRESHOLD = 3_000;

/** 长任务上报阈值(ms) */
const LONG_TASK_REPORT_THRESHOLD = 1_000;

/** 长任务上报最小间隔(ms)，避免刷屏 */
const LONG_TASK_REPORT_INTERVAL = 5_000;

const MAX_PHASE_HISTORY = 16;

const MAX_REPORTS = 12;

/** 关键过渡最大存活时长(ms)：超时视为泄漏（某分支未走到 end），不再阻塞自动刷新 */
const CRITICAL_TTL = 30_000;

export interface StallPhaseEntry {
  phase: string;
  at: number;
  detail?: Record<string, unknown>;
}

export interface StallReport {
  id: string;
  kind: 'frozen-session' | 'main-thread-blocked' | 'long-task';
  /** 事件被发现的时刻（epoch ms，可与网关访问日志交叉比对） */
  at: number;
  atISO: string;
  /** 事件发生时所在阶段 */
  phase: string;
  phaseAt: number;
  /** 停摆时长（frozen-session：上一会话心跳停摆到本次启动的间隔） */
  gapMs?: number;
  /** 阻塞时长（main-thread-blocked / long-task） */
  blockedMs?: number;
  confidence?: 'high' | 'low';
  note?: string;
  phaseHistory: StallPhaseEntry[];
  meta: Record<string, unknown>;
}

interface HeartbeatRecord {
  phase: string;
  at: number;
  visible: boolean;
  exit: 'clean' | 'unclean';
  history: StallPhaseEntry[];
}

interface LongTaskStats {
  count: number;
  maxMs: number;
  totalMs: number;
  lastAt: number;
  worstPhase: string;
}

let started = false;
let reportSeq = 0;
let currentPhase = 'module:load';
let currentPhaseAt = Date.now();
let phaseHistory: StallPhaseEntry[] = [];
let reports: StallReport[] = [];
let heartbeatTimer: number | undefined;
let lastTick = 0;
let tickBaselined = false;
let lastLongTaskReportAt = 0;

const criticalTransitions = new Map<string, number>();

let longTaskStats: LongTaskStats = { count: 0, maxMs: 0, totalMs: 0, lastAt: 0, worstPhase: '' };

function nextReportId(): string {
  reportSeq += 1;
  return `${Date.now().toString(36)}-${reportSeq}`;
}

function safeGet(storage: Storage | undefined, key: string): string | null {
  try {
    return storage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function safeSet(storage: Storage | undefined, key: string, value: string) {
  try {
    storage?.setItem(key, value);
  } catch {
    // 隐私模式 / 配额不足：静默降级到内存
  }
}

function readReports(): StallReport[] {
  const raw = safeGet(window.localStorage, REPORT_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as StallReport[]) : [];
  } catch {
    return [];
  }
}

function readHeartbeat(): HeartbeatRecord | null {
  const raw = safeGet(window.sessionStorage, HB_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as HeartbeatRecord;
  } catch {
    return null;
  }
}

/** 环境快照：仅布尔/数字/脱敏文本，禁止写入凭据 */
function getMeta(): Record<string, unknown> {
  const perf = performance as Performance & { memory?: { usedJSHeapSize?: number } };
  const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
  const heap = perf.memory?.usedJSHeapSize;

  return {
    buildTime: document.querySelector('meta[name="buildTime"]')?.getAttribute('content') || null,
    href: window.location.href.slice(0, 300),
    visible: document.visibilityState,
    onLine: navigator.onLine,
    hasToken: Boolean(localStg.get('token')),
    memMB: typeof heap === 'number' ? Math.round(heap / 1048576) : null,
    nav: navEntry
      ? {
          type: navEntry.type,
          domInteractive: Math.round(navEntry.domInteractive),
          loadEnd: Math.round(navEntry.loadEventEnd)
        }
      : null,
    ua: navigator.userAgent.slice(0, 160),
    longTasks: { ...longTaskStats }
  };
}

function pushReport(report: StallReport) {
  reports = [report, ...reports].slice(0, MAX_REPORTS);
  safeSet(window.localStorage, REPORT_KEY, JSON.stringify(reports));

  // eslint-disable-next-line no-console
  console.warn('[stall-watchdog]', report.kind, report);

  const blockedMs = report.blockedMs ?? report.gapMs ?? 0;
  if (blockedMs >= BLOCK_THRESHOLD) {
    const seconds = Math.max(1, Math.round(blockedMs / 1000));
    window.$message?.warning(
      `检测到页面曾无响应约 ${seconds}s，已记录诊断信息（控制台执行 window.__forgeStallDump() 查看）`
    );
  }
}

function writeHeartbeat(exit: 'clean' | 'unclean' = 'unclean') {
  const record: HeartbeatRecord = {
    phase: currentPhase,
    at: currentPhaseAt,
    visible: document.visibilityState === 'visible',
    exit,
    history: phaseHistory.slice(-6)
  };
  safeSet(window.sessionStorage, HB_KEY, JSON.stringify(record));
}

function makeReport(
  kind: StallReport['kind'],
  extra: Partial<Pick<StallReport, 'gapMs' | 'blockedMs' | 'confidence' | 'note' | 'phase' | 'phaseAt'>>
): StallReport {
  const at = Date.now();
  return {
    id: nextReportId(),
    kind,
    at,
    atISO: new Date(at).toISOString(),
    phase: extra.phase ?? currentPhase,
    phaseAt: extra.phaseAt ?? currentPhaseAt,
    gapMs: extra.gapMs,
    blockedMs: extra.blockedMs,
    confidence: extra.confidence,
    note: extra.note,
    phaseHistory: phaseHistory.slice(-MAX_PHASE_HISTORY),
    meta: getMeta()
  };
}

/**
 * 打点：记录关键链路阶段（同时刷新心跳，使冻结报告能回溯到最后一个落盘阶段）
 *
 * @param phase 阶段名，约定 `域:动作`，如 `auth:login:start`、`req:pending`
 * @param detail 仅允许放布尔 / 数字 / 短字符串
 */
export function markPhase(phase: string, detail?: Record<string, unknown>) {
  const at = Date.now();
  currentPhase = phase;
  currentPhaseAt = at;
  phaseHistory.push(detail ? { phase, at, detail } : { phase, at });
  if (phaseHistory.length > MAX_PHASE_HISTORY) {
    phaseHistory = phaseHistory.slice(-MAX_PHASE_HISTORY);
  }
  writeHeartbeat();
}

/** 当前阶段（供自动刷新前置条件等使用） */
export function getCurrentPhase(): { phase: string; at: number } {
  return { phase: currentPhase, at: currentPhaseAt };
}

/** 进入关键过渡（登录 / 路由过渡）：期间不执行自动刷新，避免打断关键链路 */
export function beginCriticalTransition(name: string) {
  criticalTransitions.set(name, Date.now());
}

/** 退出关键过渡 */
export function endCriticalTransition(name: string) {
  criticalTransitions.delete(name);
}

/** 是否存在进行中的关键过渡（逾期未结束的按泄漏清理） */
export function isCriticalTransitionActive(): boolean {
  const now = Date.now();
  let active = false;

  criticalTransitions.forEach((at, name) => {
    if (now - at > CRITICAL_TTL) {
      criticalTransitions.delete(name);
      return;
    }
    active = true;
  });

  return active;
}

/** 读取结构化冻结报告（按时间倒序） */
export function getStallReports(): StallReport[] {
  reports = readReports();
  return reports;
}

/** 打印结构化冻结报告 */
export function dumpStallReports(): StallReport[] {
  const list = getStallReports();
  // eslint-disable-next-line no-console
  console.info('[stall-watchdog] reports', list);
  if (list.length) {
    // eslint-disable-next-line no-console
    console.table(
      list.map(item => ({
        kind: item.kind,
        at: item.atISO,
        phase: item.phase,
        gapMs: item.gapMs,
        blockedMs: item.blockedMs,
        buildTime: item.meta.buildTime as string,
        visible: item.meta.visible as boolean
      }))
    );
  }
  return list;
}

/** 清空结构化冻结报告 */
export function clearStallReports() {
  reports = [];
  safeSet(window.localStorage, REPORT_KEY, '[]');
}

/** 启动时比对上一会话心跳：无正常退出且心跳陈旧 → 说明上一会话主线程停转 */
function checkPreviousSession() {
  const prev = readHeartbeat();
  if (!prev?.at || prev.exit === 'clean') return;

  const gap = Date.now() - prev.at;
  if (gap < STALE_THRESHOLD || gap > STALE_MAX_GAP) return;

  pushReport(
    makeReport('frozen-session', {
      gapMs: gap,
      phase: prev.phase,
      phaseAt: prev.at,
      confidence: prev.visible ? 'high' : 'low',
      note: prev.visible
        ? 'previous session heartbeat stopped while visible, no clean exit'
        : 'previous session heartbeat stopped while hidden (renderer frozen or tab killed)'
    })
  );
}

function setupLongTaskObserver() {
  if (!('PerformanceObserver' in window)) return;

  try {
    const observer = new PerformanceObserver(list => {
      list.getEntries().forEach(entry => {
        const duration = entry.duration;
        longTaskStats.count += 1;
        longTaskStats.totalMs += duration;
        longTaskStats.lastAt = Date.now();
        if (duration > longTaskStats.maxMs) {
          longTaskStats.maxMs = duration;
          longTaskStats.worstPhase = currentPhase;
        }

        if (duration < LONG_TASK_REPORT_THRESHOLD) return;
        if (Date.now() - lastLongTaskReportAt < LONG_TASK_REPORT_INTERVAL) return;

        lastLongTaskReportAt = Date.now();
        pushReport(
          makeReport('long-task', {
            blockedMs: Math.round(duration),
            note: `longtask ${Math.round(duration)}ms`
          })
        );
      });
    });

    observer.observe({ entryTypes: ['longtask'] });
  } catch {
    // 浏览器不支持 longtask：忽略该通道
  }
}

/** 心跳 tick：页面可见时用定时器延迟量判定主线程是否被阻塞；隐藏时浏览器会节流定时器，不做判定 */
function heartbeatTick() {
  const now = Date.now();
  const lag = now - lastTick - HEARTBEAT_INTERVAL;
  lastTick = now;

  if (document.visibilityState !== 'visible') {
    tickBaselined = false;
    return;
  }

  if (!tickBaselined) {
    tickBaselined = true;
    return;
  }

  if (lag > BLOCK_THRESHOLD) {
    pushReport(
      makeReport('main-thread-blocked', {
        blockedMs: Math.round(lag),
        note: 'heartbeat timer delayed'
      })
    );
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    // 回到前台时重新基线，避免把后台节流误判为阻塞
    lastTick = Date.now();
    tickBaselined = false;
    writeHeartbeat();
  }
}

function handlePageExit() {
  writeHeartbeat('clean');
}

/** 启动观测器（幂等）：必须在应用初始化最早期调用，才能覆盖登录与路由链路 */
export function startStallWatchdog() {
  if (started) return;
  started = true;

  reports = readReports();
  checkPreviousSession();

  lastTick = Date.now();
  tickBaselined = false;

  markPhase('watchdog:start');

  setupLongTaskObserver();

  document.addEventListener('visibilitychange', handleVisibilityChange);
  window.addEventListener('pagehide', handlePageExit);
  window.addEventListener('beforeunload', handlePageExit);

  heartbeatTimer = window.setInterval(heartbeatTick, HEARTBEAT_INTERVAL);

  Object.assign(window, {
    __forgeStallReports: getStallReports,
    __forgeStallDump: dumpStallReports,
    __forgeStallClear: clearStallReports,
    __forgeStallStats: () => ({ phase: currentPhase, phaseAt: currentPhaseAt, longTasks: { ...longTaskStats } })
  });
}

/** 停止观测器（仅测试使用） */
export function stopStallWatchdog() {
  if (heartbeatTimer) {
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = undefined;
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange);
  window.removeEventListener('pagehide', handlePageExit);
  window.removeEventListener('beforeunload', handlePageExit);
  started = false;
}
