import type { App } from 'vue';
import { getCurrentPhase, isCriticalTransitionActive, markPhase } from '@/utils/stall-watchdog';

export function setupAppErrorHandle(app: App) {
  app.config.errorHandler = (err, vm, info) => {
    // eslint-disable-next-line no-console
    console.error(err, vm, info);
  };
}

export function setupAppVersionNotification() {
  // Update check interval in milliseconds
  const UPDATE_CHECK_INTERVAL = 30 * 1000;

  // 自动刷新前置条件：关键过渡（登录 / 路由过渡）进行中时推迟刷新
  const MAX_DEFER_TIMES = 4;
  const DEFER_RECHECK_DELAY = 15 * 1000;

  // dev 环境也生效：本地开发时后端/网关重建同样会导致旧连接失效
  const canAutoUpdateApp = import.meta.env.VITE_AUTOMATICALLY_DETECT_UPDATE === 'Y';
  if (!canAutoUpdateApp) return;

  let updateInterval: ReturnType<typeof setInterval> | undefined;
  let deferRecheckTimer: ReturnType<typeof setTimeout> | undefined;
  let deferredTimes = 0;

  const checkForUpdates = async () => {
    const buildTime = await getHtmlBuildTime();

    // If failed to get build time or build time hasn't changed, no update is needed.
    if (!buildTime || buildTime === BUILD_TIME) {
      return;
    }

    markPhase('update:detected', { from: BUILD_TIME, to: buildTime });

    // 刷新前置条件：关键过渡进行中先推迟，避免自动刷新与登录 / 路由链路竞争
    if (isCriticalTransitionActive()) {
      deferredTimes += 1;

      if (deferredTimes <= MAX_DEFER_TIMES) {
        markPhase('update:deferred', { times: deferredTimes, phase: getCurrentPhase().phase });
        clearTimeout(deferRecheckTimer);
        deferRecheckTimer = setTimeout(checkForUpdates, DEFER_RECHECK_DELAY);
        return;
      }

      // 超过推迟上限仍然刷新：避免关键过渡异常未结束导致标签页长期停留在旧版本
      markPhase('update:defer-limit', { times: deferredTimes });
    }

    // 检测到新版本：直接自动刷新，避免旧标签页停留在旧前端（配合请求层超时兜底）
    // eslint-disable-next-line no-console
    console.info('[app] buildTime changed, auto reload', BUILD_TIME, '->', buildTime);
    markPhase('update:reload', { to: buildTime });
    location.reload();
  };

  const startUpdateInterval = () => {
    if (updateInterval) {
      clearInterval(updateInterval);
    }
    updateInterval = setInterval(checkForUpdates, UPDATE_CHECK_INTERVAL);
  };

  // Check for updates when the document is visible
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      // 回到前台重新判定：重置推迟计数，避免残留过渡状态导致持续推迟
      deferredTimes = 0;
      checkForUpdates();
      startUpdateInterval();
    }
  });

  // Start the update interval
  startUpdateInterval();
}

async function getHtmlBuildTime(): Promise<string | null> {
  const baseUrl = import.meta.env.VITE_BASE_URL || '/';

  // 原生 fetch 无超时兜底：挂 AbortController 防止半开连接下永久挂起（同请求层兜底思路）
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 10 * 1000);

  try {
    const res = await fetch(`${baseUrl}index.html?time=${Date.now()}`, { signal: controller.signal });

    if (!res.ok) {
      markPhase('update:selfcheck-failed', { status: res.status });
      return null;
    }

    const html = await res.text();
    const match = html.match(/<meta name="buildTime" content="(.*)">/);
    return match?.[1] || null;
  } catch (error) {
    // 自检失败打点：冻结场景下自检请求会连同心跳一起停摆，落盘的最后一条失败时间可界定停摆起点
    markPhase('update:selfcheck-failed', { message: (error as Error)?.message?.slice(0, 80) });
    window.console.error('getHtmlBuildTime error:', error);
    return null;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
