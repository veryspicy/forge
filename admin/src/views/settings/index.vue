<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { NButton, NCard, NFormItem, NInput, NSpin, NSwitch } from 'naive-ui';
import { get, put } from '@/service/api/helper';

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

onMounted(loadSettings);
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
