// Auth middleware — guards admin and authenticated routes
export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated } = useAuth();
  const localePath = useLocalePath();

  if (!isAuthenticated.value) {
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
