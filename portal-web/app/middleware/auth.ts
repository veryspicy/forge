// Auth middleware — guards admin and authenticated routes
export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore();
  const localePath = useLocalePath();

  if (!authStore.isAuthenticated) {
    const redirectPath = to.fullPath;
    return navigateTo(localePath(`/login?redirect=${encodeURIComponent(redirectPath)}`));
  }

  // Admin routes: currently placeholder — logged-in users can access
  // Future: check role from user object
  if (to.path.startsWith("/admin")) {
    // Role check will be tightened later
    return;
  }
});
