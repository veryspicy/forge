import { $t } from '@/locales';

/**
 * 旧标签页自愈刷新守卫（docs/DEV-RULES.md §18）
 *
 * admin 重新构建/重启容器后，停留在旧页面的标签页会出现两类"卡死"：
 * ① 复用指向旧容器的失效 keep-alive 连接，请求无限挂起（XHR timeout 事件不触发）；
 * ② 路由懒加载引用的旧 chunk 已被新构建替换，动态 import 失败，表现为点菜单/按钮无反应或白屏。
 * 两者都只能靠"强制刷新"自愈，因此**必须共用同一个防循环计数**——
 * 各开一个 key 会让同一 tab 的实际刷新次数翻倍，更难命中上限保护，反而刷成死循环。
 */

/** 同一 tab 内自愈刷新的防循环计数 key：请求成功或达到上限时清零 */
export const STALE_RELOAD_KEY = 'forge:stale-reload-count';

/** 同一 tab 内自愈刷新次数上限，超过则放弃自动刷新，交回原有错误处理 */
export const STALE_RELOAD_MAX = 3;

/** 刷新前延迟（ms）：留出提示渲染时间，避免用户看不到任何反馈 */
const RELOAD_DELAY = 800;

/**
 * 安排一次自愈刷新（受防循环计数约束）
 *
 * @param options.quiet 静默刷新不弹提示。chunk 加载失败场景必须静默：
 *                      此时 message 组件自身可能就在未加载成功的 chunk 里，弹提示会二次抛错。
 * @returns 是否已安排刷新；返回 false 表示已达上限，调用方应继续走原有错误处理分支
 */
export function reloadOnStaleConnection(options?: { quiet?: boolean }): boolean {
  const count = Number(sessionStorage.getItem(STALE_RELOAD_KEY) || '0') + 1;
  sessionStorage.setItem(STALE_RELOAD_KEY, String(count));

  if (count > STALE_RELOAD_MAX) {
    sessionStorage.removeItem(STALE_RELOAD_KEY);
    return false;
  }

  if (!options?.quiet) {
    window.$message?.warning($t('request.timeoutReloading'));
  }

  window.setTimeout(() => {
    window.location.reload();
  }, RELOAD_DELAY);

  return true;
}

/**
 * 动态 import / chunk 加载失败的特征串
 *
 * 不同浏览器与 Vite 版本抛出的文案不一致（Chrome/Firefox/Safari 各一套），
 * 且 Vite 会包装成 "Importing a module script failed"，故全部覆盖。
 */
const CHUNK_LOAD_ERROR_PATTERNS = [
  /Failed to fetch dynamically imported module/i,
  /Importing a module script failed/i,
  /error loading dynamically imported module/i,
  /Loading chunk \S+ failed/i,
  /Loading CSS chunk/i,
  /Unable to preload CSS/i,
  /ChunkLoadError/i
];

/** 判断错误是否为"资源已被替换/加载失败"类（旧标签页引用重建后不存在的 chunk） */
export function isChunkLoadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error ?? '');
  return CHUNK_LOAD_ERROR_PATTERNS.some(pattern => pattern.test(message));
}
