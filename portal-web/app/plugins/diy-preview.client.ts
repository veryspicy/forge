/**
 * DIY 编辑器预览模式客户端插件
 *
 * 在 iframe 内（DIY 预览）时，给所有 SPA 导航自动补 preview=true query，
 * 防止 auth middleware 因缺少 preview query 而 redirect 到登录页。
 */
export default defineNuxtPlugin(() => {
  let inIframe = false;
  try {
    inIframe = window.top !== window.self;
  } catch {
    inIframe = false;
  }
  if (!inIframe) return;

  // 全局 beforeEach 守卫 — 在导航前给目标路由补 preview=true
  const router = useRouter();
  router.beforeEach((to) => {
    if (to.query?.preview !== 'true' && to.query?.preview !== '1') {
      return { path: to.path, query: { ...to.query, preview: 'true' }, hash: to.hash };
    }
  });
});
