import type { App } from 'vue';
import {
  type RouterHistory,
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory
} from 'vue-router';
import { isChunkLoadError, reloadOnStaleConnection } from '@/service/request/stale-reload';
import { createBuiltinVueRoutes } from './routes/builtin';
import { createRouterGuard } from './guard';

const { VITE_ROUTER_HISTORY_MODE = 'history', VITE_BASE_URL } = import.meta.env;

const historyCreatorMap: Record<Env.RouterHistoryMode, (base?: string) => RouterHistory> = {
  hash: createWebHashHistory,
  history: createWebHistory,
  memory: createMemoryHistory
};

export const router = createRouter({
  history: historyCreatorMap[VITE_ROUTER_HISTORY_MODE](VITE_BASE_URL),
  routes: createBuiltinVueRoutes()
});

/**
 * 旧标签页 chunk 自愈守卫（docs/DEV-RULES.md §18）
 *
 * admin 重新构建后，停留在旧页面的标签页会请求已被替换的动态 chunk：vue-router 懒加载失败
 * 只中止导航、不抛到全局，页面表现为"点菜单没反应/白屏"。这里统一收敛为强制刷新拉取新产物，
 * 与请求层的失效连接刷新共用同一防循环计数（admin/src/service/request/stale-reload.ts）。
 */
function setupStaleChunkGuards() {
  router.onError(error => {
    if (isChunkLoadError(error)) {
      reloadOnStaleConnection({ quiet: true });
    }
  });

  // Vite 动态 import 失败会派发该事件；不 preventDefault 则错误继续向上抛（控制台报错 + 白屏）
  window.addEventListener('vite:preloadError', event => {
    event.preventDefault();
    reloadOnStaleConnection({ quiet: true });
  });
}

/** Setup Vue Router */
export async function setupRouter(app: App) {
  setupStaleChunkGuards();
  app.use(router);
  createRouterGuard(router);
  await router.isReady();
}
