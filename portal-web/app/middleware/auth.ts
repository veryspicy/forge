// Auth middleware — guards admin and authenticated routes
export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore();
  const localePath = useLocalePath();

  // DIY 编辑器预览模式：query.preview=true 时跳过鉴权
  if (to.query?.preview === 'true' || to.query?.preview === '1') {
    return;
  }

  // 客户端 SPA 导航时，iframe 内（DIY 预览）跳过鉴权
  if (import.meta.client) {
    try {
      if (window.top !== window.self) {
        return;
      }
    } catch { /* cross-origin: not in iframe */ }
  }

  if (!authStore.isAuthenticated) {
    const redirectPath = to.fullPath;
    return navigateTo(localePath(`/login?redirect=${encodeURIComponent(redirectPath)}`));
  }

  // Admin routes: currently placeholder — logged-in users can access
  if (to.path.startsWith("/admin")) {
    return;
  }
});
