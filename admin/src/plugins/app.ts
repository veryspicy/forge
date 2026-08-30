import type { App } from 'vue';

export function setupAppErrorHandle(app: App) {
  app.config.errorHandler = (err, vm, info) => {
    // eslint-disable-next-line no-console
    console.error(err, vm, info);
  };
}

export function setupAppVersionNotification() {
  // Update check interval in milliseconds
  const UPDATE_CHECK_INTERVAL = 30 * 1000;

  // dev 环境也生效：本地开发时后端/网关重建同样会导致旧连接失效
  const canAutoUpdateApp = import.meta.env.VITE_AUTOMATICALLY_DETECT_UPDATE === 'Y';
  if (!canAutoUpdateApp) return;

  let updateInterval: ReturnType<typeof setInterval> | undefined;

  const checkForUpdates = async () => {
    const buildTime = await getHtmlBuildTime();

    // If failed to get build time or build time hasn't changed, no update is needed.
    if (!buildTime || buildTime === BUILD_TIME) {
      return;
    }

    // 检测到新版本：直接自动刷新，避免旧标签页停留在旧前端（配合请求层超时兜底）
    // eslint-disable-next-line no-console
    console.info('[app] buildTime changed, auto reload', BUILD_TIME, '->', buildTime);
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
      return null;
    }

    const html = await res.text();
    const match = html.match(/<meta name="buildTime" content="(.*)">/);
    return match?.[1] || null;
  } catch (error) {
    window.console.error('getHtmlBuildTime error:', error);
    return null;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
