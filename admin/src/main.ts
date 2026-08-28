import { createApp } from 'vue';
import './plugins/assets';
import { setupVueRootValidator } from 'vite-plugin-vue-transition-root-validator/client';
import { setupAppVersionNotification, setupDayjs, setupIconifyOffline, setupLoading, setupNProgress, setupPermissionDirective } from './plugins';
import { setupStore } from './store';
import { setupRouter, router } from './router';
import { getLocale, setupI18n } from './locales';
import App from './App.vue';

const CHUNK_RETRY_KEY = 'forge-admin-chunk-retry';

function isChunkLoadError(message: string) {
  return /Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk|error loading dynamically imported module/i.test(
    message ?? ''
  );
}

/** 动态 import chunk 加载失败自动恢复：自动刷新一次（sessionStorage 防循环） */
function setupChunkErrorRecovery() {
  const reloadOnce = () => {
    if (sessionStorage.getItem(CHUNK_RETRY_KEY)) {
      // 刷新过一次仍失败，说明不是缓存残留问题，停止自动恢复
      sessionStorage.removeItem(CHUNK_RETRY_KEY);
      return;
    }
    sessionStorage.setItem(CHUNK_RETRY_KEY, '1');
    window.location.reload();
  };

  window.addEventListener('unhandledrejection', event => {
    const message = event.reason instanceof Error ? event.reason.message : String(event.reason ?? '');
    if (isChunkLoadError(message)) {
      event.preventDefault();
      reloadOnce();
    }
  });

  router.onError(error => {
    const message = error instanceof Error ? error.message : String(error ?? '');
    if (isChunkLoadError(message)) {
      reloadOnce();
    }
  });
}

async function setupApp() {
  setupLoading();

  setupNProgress();

  setupIconifyOffline();

  setupDayjs();

  setupChunkErrorRecovery();

  const app = createApp(App);

  setupStore(app);

  setupPermissionDirective(app);

  await setupRouter(app);

  setupI18n(app);

  setupAppVersionNotification();

  setupVueRootValidator(app, {
    lang: getLocale() === 'zh-CN' ? 'zh' : 'en'
  });

  app.mount('#app');
}

setupApp();
