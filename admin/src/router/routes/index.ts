import type { ElegantRoute } from '@elegant-router/types';
import { generatedRoutes } from '../elegant/routes';
import { layouts, views } from '../elegant/imports';
import { transformElegantRoutesToVueRoutes } from '../elegant/transform';

const customRoutes = [
  // ============ 1. Dashboard ============
  {
    name: 'dashboard',
    path: '/dashboard',
    component: 'layout.base$view.dashboard',
    meta: {
      title: 'Dashboard',
      i18nKey: 'route.dashboard',
      icon: 'mdi:monitor-dashboard',
      order: 1,
      roles: ['super_admin', 'admin', 'operator', 'support']
    }
  },

  // ============ 2. Merchandise ============
  {
    name: 'merchandise',
    path: '/merchandise',
    meta: {
      title: 'Merchandise',
      i18nKey: 'route.merchandise',
      icon: 'mdi:store',
      order: 2,
      roles: ['super_admin', 'admin', 'operator']
    },
    redirect: '/products',
    children: [
      {
        name: 'products',
        path: '/products',
        component: 'layout.base$view.products',
        meta: {
          title: 'Products',
          i18nKey: 'route.products',
          icon: 'mdi:package-variant',
          order: 1,
          roles: ['super_admin', 'admin', 'operator']
        }
      },
      {
        name: 'products-new',
        path: '/products/new',
        component: 'layout.base$view.products-new',
        meta: {
          title: 'New Product',
          i18nKey: 'route.products-new',
          hideInMenu: true,
          activeMenu: 'products',
          roles: ['super_admin', 'admin', 'operator']
        }
      },
      {
        name: 'products-detail',
        path: '/products/:id',
        component: 'layout.base$view.products-detail',
        meta: {
          title: 'Edit Product',
          i18nKey: 'route.products-detail',
          hideInMenu: true,
          activeMenu: 'products',
          roles: ['super_admin', 'admin', 'operator']
        }
      },
      {
        name: 'suppliers',
        path: '/suppliers',
        component: 'layout.base$view.suppliers',
        meta: {
          title: 'Suppliers',
          i18nKey: 'route.suppliers',
          icon: 'mdi:truck-delivery',
          order: 2,
          roles: ['super_admin', 'admin']
        }
      },
      {
        name: 'pricing',
        path: '/pricing',
        component: 'layout.base$view.pricing',
        meta: {
          title: 'Pricing',
          i18nKey: 'route.pricing',
          icon: 'mdi:cash-multiple',
          order: 3,
          roles: ['super_admin', 'admin']
        }
      }
    ]
  },

  // ============ 3. Sales ============
  {
    name: 'sales',
    path: '/sales',
    meta: {
      title: 'Sales',
      i18nKey: 'route.sales',
      icon: 'mdi:shopping',
      order: 3,
      roles: ['super_admin', 'admin', 'operator', 'support']
    },
    redirect: '/orders',
    children: [
      {
        name: 'orders',
        path: '/orders',
        component: 'layout.base$view.orders',
        meta: {
          title: 'Orders',
          i18nKey: 'route.orders',
          icon: 'mdi:cart',
          order: 1,
          roles: ['super_admin', 'admin', 'operator', 'support']
        }
      },
      {
        name: 'orders-detail',
        path: '/orders/:id',
        component: 'layout.base$view.orders-detail',
        meta: {
          title: 'Order Detail',
          i18nKey: 'route.orders-detail',
          hideInMenu: true,
          activeMenu: 'orders',
          roles: ['super_admin', 'admin', 'operator', 'support']
        }
      },
      {
        name: 'shipments',
        path: '/shipments',
        component: 'layout.base$view.shipments',
        meta: {
          title: 'Shipments',
          i18nKey: 'route.shipments',
          icon: 'mdi:package-variant-closed',
          order: 2,
          roles: ['super_admin', 'admin', 'operator']
        }
      }
    ]
  },

  // ============ 4. Customers ============
  {
    name: 'customers',
    path: '/customers',
    component: 'layout.base$view.users',
    meta: {
      title: 'Customers',
      i18nKey: 'route.customers',
      icon: 'mdi:account-group',
      order: 4,
      roles: ['super_admin', 'admin', 'operator']
    }
  },

  // ============ 5. AI Probe ============
  {
    name: 'ai-probe',
    path: '/ai-probe',
    component: 'layout.base$view.ai-probe',
    meta: {
      title: 'AI Probe',
      i18nKey: 'route.ai-probe',
      icon: 'mdi:robot',
      order: 5,
      roles: ['super_admin', 'admin', 'support']
    }
  },

  // ============ 6. Site ============
  {
    name: 'site',
    path: '/site',
    meta: {
      title: 'Site',
      i18nKey: 'route.site',
      icon: 'mdi:web',
      order: 6,
      roles: ['super_admin', 'admin']
    },
    redirect: '/site/config',
    children: [
      {
        name: 'site-config',
        path: '/site/config',
        component: 'layout.base$view.site',
        meta: {
          title: 'Site Config',
          i18nKey: 'route.site-config',
          icon: 'mdi:cog-outline',
          order: 1,
          roles: ['super_admin', 'admin']
        }
      },
      {
        name: 'site-decoration',
        path: '/site/decoration',
        component: 'layout.base$view.diy',
        meta: {
          title: 'Decoration',
          i18nKey: 'route.site-decoration',
          icon: 'mdi:hammer-wrench',
          order: 2,
          roles: ['super_admin', 'admin', 'operator']
        }
      },
      {
        name: 'site-decoration-editor',
        path: '/site/decoration/editor/:id',
        component: 'layout.base$view.diy-editor',
        meta: {
          title: 'Page Editor',
          i18nKey: 'route.site-decoration-editor',
          hideInMenu: true,
          activeMenu: 'site-decoration',
          roles: ['super_admin', 'admin', 'operator']
        }
      }
    ]
  },

  // ============ 8. System ============
  {
    name: 'system',
    path: '/system',
    meta: {
      title: 'System',
      i18nKey: 'route.system',
      icon: 'mdi:cog',
      order: 8,
      roles: ['super_admin', 'admin']
    },
    redirect: '/admin-users',
    children: [
      {
        name: 'admin-users',
        path: '/admin-users',
        component: 'layout.base$view.admin-users',
        meta: {
          title: 'Admin Users',
          i18nKey: 'route.admin-users',
          icon: 'mdi:account-cog',
          order: 1,
          roles: ['super_admin', 'admin']
        }
      },
      {
        name: 'roles',
        path: '/roles',
        component: 'layout.base$view.roles',
        meta: {
          title: 'Roles',
          i18nKey: 'route.roles',
          icon: 'mdi:shield-key',
          order: 2,
          roles: ['super_admin', 'admin']
        }
      },
      {
        name: 'settings',
        path: '/settings',
        component: 'layout.base$view.settings',
        meta: {
          title: 'Settings',
          i18nKey: 'route.settings',
          icon: 'mdi:cog',
          order: 3,
          roles: ['super_admin', 'admin']
        }
      }
    ]
  }
];

export function createStaticRoutes() {
  const constantRoutes: ElegantRoute[] = [];
  const authRoutes: ElegantRoute[] = [];

  // Filter out generated routes that are already defined in customRoutes
  // to prevent flat auto-generated routes from overriding the nested menu structure
  // Auto-generated routes to ignore (custom routes already define them differently)
  const ignoreGeneratedRouteNames = new Set(['users']);
  const customRouteNames = new Set(customRoutes.flatMap((r: any) => {
    const names = [r.name];
    if (r.children) {
      r.children.forEach((c: any) => names.push(c.name));
    }
    return names;
  }));
  const filteredGeneratedRoutes = generatedRoutes.filter((r: any) => !customRouteNames.has(r.name) && !ignoreGeneratedRouteNames.has(r.name));

  [...customRoutes, ...filteredGeneratedRoutes].forEach((item: any) => {
    if (item.meta?.constant) {
      constantRoutes.push(item);
    } else {
      authRoutes.push(item);
    }
  });

  return {
    constantRoutes,
    authRoutes
  };
}

export function getAuthVueRoutes(routes: ElegantConstRoute[]) {
  return transformElegantRoutesToVueRoutes(routes, layouts, views);
}
