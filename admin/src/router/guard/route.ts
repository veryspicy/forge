import type { LocationQueryRaw, RouteLocationNormalized, RouteLocationRaw, Router } from 'vue-router';
import type { RouteKey, RoutePath } from '@elegant-router/types';
import { useAuthStore } from '@/store/modules/auth';
import { useRouteStore } from '@/store/modules/route';
import { localStg } from '@/utils/storage';
import { beginCriticalTransition, endCriticalTransition, markPhase } from '@/utils/stall-watchdog';
import { getRouteName } from '@/router/elegant/transform';

/**
 * create route guard
 *
 * @param router router instance
 */
export function createRouteGuard(router: Router) {
  router.beforeEach(async (to, from) => {
    markPhase('guard:enter', { to: String(to.name ?? ''), from: String(from.name ?? '') });
    // 路由过渡期间标记关键过渡：自动刷新的前置条件会推迟，避免导航被自动刷新打断
    beginCriticalTransition('route-nav');

    try {
      const location = await initRoute(to);

      if (location) {
        return location;
      }

      const authStore = useAuthStore();

      const rootRoute: RouteKey = 'root';
      const loginRoute: RouteKey = 'login';

      const isLogin = Boolean(localStg.get('token'));
      const needLogin = !to.meta.constant;
      const routeRoles = to.meta.roles || [];

      const hasRole = authStore.userInfo.roles.some(role => routeRoles.includes(role));
      const hasAuth = authStore.isStaticSuper || !routeRoles.length || hasRole;

      // if it is login route when logged in, then switch to the root page
      if (to.name === loginRoute && isLogin) {
        return { name: rootRoute };
      }

      // if the route does not need login, then it is allowed to access directly
      if (!needLogin) {
        return handleRouteSwitch(to, from);
      }

      // the route need login but the user is not logged in, then switch to the login page
      if (!isLogin) {
        return { name: loginRoute, query: { redirect: to.fullPath } };
      }

      // if the user is logged in but does not have authorization,
      // show a message and stay on current page or redirect to home
      if (!hasAuth) {
        window.$message?.warning('您没有权限访问该页面');
        const rootRouteKey: RouteKey = 'root';
        if (from.name && from.name !== rootRouteKey) {
          return false;
        }
        return { name: rootRouteKey };
      }

      // switch route normally
      return handleRouteSwitch(to, from);
    } finally {
      markPhase('guard:leave');
      endCriticalTransition('route-nav');
    }
  });
}

/**
 * initialize route
 *
 * @param to to route
 */
async function initRoute(to: RouteLocationNormalized): Promise<RouteLocationRaw | null> {
  const routeStore = useRouteStore();

  const notFoundRoute: RouteKey = 'not-found';
  const isNotFoundRoute = to.name === notFoundRoute;

  markPhase('guard:init-route:start', { path: to.fullPath.slice(0, 120), name: String(to.name ?? '') });

  // if the constant route is not initialized, then initialize the constant route
  if (!routeStore.isInitConstantRoute) {
    await routeStore.initConstantRoute();

    // the route is captured by the "not-found" route because the constant route is not initialized
    // after the constant route is initialized, redirect to the original route
    const path = to.fullPath;
    const location: RouteLocationRaw = {
      path,
      replace: true,
      query: to.query,
      hash: to.hash
    };

    return location;
  }

  const isLogin = Boolean(localStg.get('token'));

  if (!isLogin) {
    // if the user is not logged in and the route is a constant route but not the "not-found" route, then it is allowed to access.
    if (to.meta.constant && !isNotFoundRoute) {
      routeStore.onRouteSwitchWhenNotLoggedIn();

      return null;
    }

    // if the user is not logged in, then switch to the login page
    const loginRoute: RouteKey = 'login';
    const query = getRouteQueryOfLoginRoute(to, routeStore.routeHome);

    const location: RouteLocationRaw = {
      name: loginRoute,
      query
    };

    return location;
  }

  // 残留态校正：标记为已初始化、但首页 auth 路由实际未注册（上一轮登陆链路或 reset 后遗留的 latch），
  // 先复位标记，让下面的 initAuthRoute 真正走一遍补注册；否则 dashboard 缺失会落入重定向环
  if (routeStore.isInitAuthRoute && !routeStore.getIsAuthRouteRegistered(routeStore.routeHome as RouteKey)) {
    markPhase('guard:stale-auth-flag-reset', { home: routeStore.routeHome });

    routeStore.setIsInitAuthRoute(false);
  }

  if (!routeStore.isInitAuthRoute) {
    // initialize the auth route
    markPhase('guard:init-auth:start');
    await routeStore.initAuthRoute();
    markPhase('guard:init-auth:end');

    // the route is captured by the "not-found" route because the auth route is not initialized
    // after the auth route is initialized, redirect to the original route
    if (isNotFoundRoute) {
      const rootRoute: RouteKey = 'root';
      const path = to.redirectedFrom?.name === rootRoute ? '/' : to.fullPath;

      const location: RouteLocationRaw = {
        path,
        replace: true,
        query: to.query,
        hash: to.hash
      };

      return location;
    }
  }

  routeStore.onRouteSwitchWhenLoggedIn();

  // the auth route is initialized
  // it is not the "not-found" route, then it is allowed to access
  if (!isNotFoundRoute) {
    markPhase('guard:init-route:end');

    return null;
  }

  // it is captured by the "not-found" route, then check whether the route exists
  const exist = await routeStore.getIsAuthRouteExist(to.path as RoutePath);

  markPhase('guard:init-route:end', { exist });

  if (exist) {
    window.$message?.warning('您没有权限访问该页面');

    // 环兜底：root 会重定向到首页，若首页路由未注册，返回 root 将形成
    // root → 首页 → not-found → root 无限重定向环（同步重入导致主线程停转）。
    // 此时宁可停在 not-found，也不再跳 root。
    if (routeStore.getIsAuthRouteRegistered(routeStore.routeHome as RouteKey)) {
      return { name: 'root' as RouteKey };
    }

    markPhase('guard:not-found:cycle-guard', { path: to.path.slice(0, 120) });

    return null;
  }

  return null;
}

function handleRouteSwitch(to: RouteLocationNormalized, from: RouteLocationNormalized) {
  // route with href
  if (to.meta.href) {
    window.open(to.meta.href, '_blank');

    return { path: from.fullPath, replace: true, query: from.query, hash: to.hash };
  }
}

function getRouteQueryOfLoginRoute(to: RouteLocationNormalized, routeHome: RouteKey) {
  const loginRoute: RouteKey = 'login';
  const redirect = to.fullPath;
  const [redirectPath, redirectQuery] = redirect.split('?');
  const redirectName = getRouteName(redirectPath as RoutePath);

  const isRedirectHome = routeHome === redirectName;

  const query: LocationQueryRaw = to.name !== loginRoute && !isRedirectHome ? { redirect } : {};

  if (isRedirectHome && redirectQuery) {
    query.redirect = `/?${redirectQuery}`;
  }

  return query;
}
