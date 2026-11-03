<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { NAlert, NButton, NCard, NFormItem, NInput, NSpin, NSwitch } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { get, put } from '@/service/api/helper';
import { useRouteStore } from '@/store/modules/route';
import type { MenuOrderConfig } from '@/store/modules/route/shared';

const routeStore = useRouteStore();

const loading = ref(true);
const saving = ref(false);
const saveMsg = ref('');
const saveError = ref(false);

const localSettings = reactive({
  notifications: { email_enabled: true, admin_email: '', order_alerts: true }
});

async function loadSettings() {
  try {
    const res = await get('/api/admin/v1/settings/');
    if (res.data && Object.keys(res.data).length) {
      localSettings.notifications = {
        email_enabled: true,
        admin_email: '',
        order_alerts: true,
        ...res.data.notifications
      };
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function saveAll() {
  saving.value = true;
  saveMsg.value = '';
  saveError.value = false;
  try {
    for (const [key, value] of Object.entries(localSettings)) {
      await put(`/api/admin/v1/settings/${key}`, { value });
    }
    saveMsg.value = 'Settings saved successfully.';
  } catch (e: any) {
    saveError.value = true;
    saveMsg.value = e.response?.data?.detail || 'Save failed';
  } finally {
    saving.value = false;
  }
}

/* ---------- Menu order ---------- */

const menuSaving = ref(false);
const menuMsg = ref('');
const menuError = ref(false);
const menuOrderList = ref<App.Global.Menu[]>([]);

function syncMenuOrderFromStore() {
  menuOrderList.value = routeStore.menus.map(menu => ({
    ...menu,
    children: menu.children?.map(child => ({ ...child }))
  }));
}

function collectMenuOrder(): MenuOrderConfig {
  const top = menuOrderList.value.map(menu => menu.key);
  const children: Record<string, string[]> = {};

  menuOrderList.value.forEach(menu => {
    if (menu.children?.length) {
      children[menu.key] = menu.children.map(child => child.key);
    }
  });

  return { top, children };
}

async function saveMenuOrder() {
  menuSaving.value = true;
  menuMsg.value = '';
  menuError.value = false;
  try {
    const order = collectMenuOrder();
    await put('/api/admin/v1/settings/menu_order', { value: order });
    routeStore.refreshMenusWithOrder(order);
    menuMsg.value = 'Menu order saved.';
  } catch (e: any) {
    menuError.value = true;
    menuMsg.value = e.response?.data?.detail || 'Save failed';
  } finally {
    menuSaving.value = false;
  }
}

async function resetMenuOrder() {
  menuSaving.value = true;
  menuMsg.value = '';
  menuError.value = false;
  try {
    await put('/api/admin/v1/settings/menu_order', { value: {} });
    routeStore.refreshMenusWithOrder(null);
    syncMenuOrderFromStore();
    menuMsg.value = 'Menu order reset to default.';
  } catch (e: any) {
    menuError.value = true;
    menuMsg.value = e.response?.data?.detail || 'Reset failed';
  } finally {
    menuSaving.value = false;
  }
}

onMounted(async () => {
  await loadSettings();
  syncMenuOrderFromStore();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <NSpin :show="loading">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Notifications -->
        <NCard :title="$t('page.settings.emailNotifications')" size="small">
          <NFormItem :label="$t('page.settings.emailNotifications')">
            <NSwitch v-model:value="localSettings.notifications.email_enabled" />
          </NFormItem>
          <NFormItem :label="$t('page.settings.adminEmail')">
            <NInput v-model:value="localSettings.notifications.admin_email" type="text" />
          </NFormItem>
          <NFormItem :label="$t('page.settings.orderAlerts')">
            <NSwitch v-model:value="localSettings.notifications.order_alerts" />
          </NFormItem>
        </NCard>

        <!-- Menu order -->
        <NCard :title="$t('page.settings.menuOrder')" size="small">
          <NAlert type="info" :show-icon="true" class="mb-3">
            {{ $t('page.settings.menuOrderTip') }}
          </NAlert>

          <div v-if="menuOrderList.length" class="flex flex-col gap-1">
            <VueDraggable v-model="menuOrderList" class="flex flex-col gap-1" item-key="key">
              <template #default>
                <div
                  v-for="menu in menuOrderList"
                  :key="menu.key"
                  class="border border-gray-200 dark:border-gray-700 rounded px-3 py-2 bg-white dark:bg-gray-800 cursor-move select-none"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-sm font-medium">{{ menu.label }}</span>
                  </div>
                  <VueDraggable
                    v-if="menu.children?.length"
                    v-model="menu.children"
                    class="flex flex-col gap-1 mt-2 pl-4"
                    item-key="key"
                  >
                    <template #default>
                      <div
                        v-for="child in menu.children"
                        :key="child.key"
                        class="border border-dashed border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-gray-50 dark:bg-gray-700/50 cursor-move select-none text-xs"
                      >
                        {{ child.label }}
                      </div>
                    </template>
                  </VueDraggable>
                </div>
              </template>
            </VueDraggable>
          </div>
          <NAlert v-else type="warning" :show-icon="true" class="mb-3">
            No menu available
          </NAlert>

          <div class="flex items-center gap-2 mt-3">
            <NButton type="primary" size="small" :loading="menuSaving" @click="saveMenuOrder">
              {{ $t('page.settings.saveMenuOrder') }}
            </NButton>
            <NButton size="small" :loading="menuSaving" @click="resetMenuOrder">
              {{ $t('page.settings.resetMenuOrder') }}
            </NButton>
          </div>

          <div
            v-if="menuMsg"
            class="text-sm p-2 mt-2 rounded"
            :class="menuError ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'"
          >
            {{ menuMsg }}
          </div>
        </NCard>
      </div>
    </NSpin>

    <div
      v-if="saveMsg"
      class="text-sm p-2 rounded"
      :class="saveError ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'"
    >
      {{ saveMsg }}
    </div>

    <div class="flex justify-end">
      <NButton type="primary" :loading="saving" @click="saveAll">{{ $t('page.settings.saveAllSettings') }}</NButton>
    </div>
  </div>
</template>
