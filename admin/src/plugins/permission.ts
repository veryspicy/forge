import type { App, Directive, DirectiveBinding } from 'vue';
import { useAuthStore } from '@/store/modules/auth';

/**
 * v-permission directive — 按钮级权限控制。
 *
 * Usage:
 *   <NButton v-permission="'products:edit'">Edit</NButton>
 *   <NButton v-permission="['products:edit', 'products:create']">Edit or Create</NButton>
 *
 * When the user lacks the required permission(s), the element is removed from the DOM.
 */
function checkPermission(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
  const authStore = useAuthStore();
  const permissions = authStore.userInfo.permissions || [];

  if (!binding.value) return;

  const required = Array.isArray(binding.value) ? binding.value : [binding.value];
  // super_admin 通配符：permissions 含 '*' 时放行任意权限码
  const hasPermission = permissions.includes('*') || required.some(p => permissions.includes(p));

  if (!hasPermission) {
    el.parentNode?.removeChild(el);
  }
}

const vPermission: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding) {
    checkPermission(el, binding);
  }
};

export function setupPermissionDirective(app: App) {
  app.directive('permission', vPermission);
}
