<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import {
  NButton, NCard, NFormItem, NGi, NGrid, NInput, NInputNumber,
  NSelect, NSpin, NSwitch,
} from 'naive-ui';
import { get, put } from '@/service/api/helper';

const loading = ref(true);
const saving = ref(false);
const saveMsg = ref('');
const saveError = ref(false);

const localSettings = reactive({
  store_name: 'Forge', currency: 'USD', region: 'AE', language: 'en',
  order_settings: { auto_review: false, max_items_per_order: 10, default_currency: 'USD', order_prefix: 'PAI', expiry_hours: 24 },
  notifications: { email_enabled: true, admin_email: '', order_alerts: true },
});

const currencyOptions = [{ label: 'USD', value: 'USD' }, { label: 'AED', value: 'AED' }, { label: 'SAR', value: 'SAR' }];
const regionOptions = ['AE', 'SA', 'KW', 'QA', 'OM', 'BH'].map(v => ({ label: v, value: v }));
const langOptions = [{ label: 'English', value: 'en' }, { label: 'Arabic', value: 'ar' }];

async function loadSettings() {
  try {
    const res = await get('/api/admin/v1/settings/');
    if (res.data && Object.keys(res.data).length) {
      Object.assign(localSettings, res.data);
      localSettings.order_settings = { auto_review: false, max_items_per_order: 10, default_currency: 'USD', order_prefix: 'PAI', expiry_hours: 24, ...res.data.order_settings };
      localSettings.notifications = { email_enabled: true, admin_email: '', order_alerts: true, ...res.data.notifications };
    }
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
}

async function saveAll() {
  saving.value = true; saveMsg.value = ''; saveError.value = false;
  try {
    for (const [key, value] of Object.entries(localSettings)) {
      await put(`/api/admin/v1/settings/${key}`, { value });
    }
    saveMsg.value = 'Settings saved successfully.';
  } catch (e: any) { saveError.value = true; saveMsg.value = e.response?.data?.detail || 'Save failed'; }
  finally { saving.value = false; }
}

onMounted(loadSettings);
</script>

<template>
  <div class="flex flex-col gap-4">
    <NSpin :show="loading">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Store Settings -->
        <NCard :title="$t('page.settings.storeSettings')" size="small" class="md:col-span-2">
          <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
            <NGi span="1"><NFormItem :label="$t('page.settings.storeName')"><NInput v-model:value="localSettings.store_name" /></NFormItem></NGi>
            <NGi span="1"><NFormItem :label="$t('page.settings.defaultCurrency')"><NSelect v-model:value="localSettings.currency" :options="currencyOptions" /></NFormItem></NGi>
            <NGi span="1"><NFormItem :label="$t('common.region')"><NSelect v-model:value="localSettings.region" :options="regionOptions" /></NFormItem></NGi>
            <NGi span="1"><NFormItem :label="$t('common.language')"><NSelect v-model:value="localSettings.language" :options="langOptions" /></NFormItem></NGi>
          </NGrid>
        </NCard>

        <!-- Order Settings -->
        <NCard :title="$t('page.settings.orderSettings')" size="small">
          <NFormItem :label="$t('page.settings.autoReview')"><NSwitch v-model:value="localSettings.order_settings.auto_review" /></NFormItem>
          <NFormItem :label="$t('page.settings.maxItemsPerOrder')"><NInputNumber v-model:value="localSettings.order_settings.max_items_per_order" :min="1" style="width:100%" /></NFormItem>
          <NFormItem :label="$t('page.settings.defaultCurrency')"><NSelect v-model:value="localSettings.order_settings.default_currency" :options="currencyOptions" /></NFormItem>
          <NFormItem :label="$t('page.settings.orderPrefix')"><NInput v-model:value="localSettings.order_settings.order_prefix" /></NFormItem>
          <NFormItem :label="$t('page.settings.expiryHours')"><NInputNumber v-model:value="localSettings.order_settings.expiry_hours" :min="1" style="width:100%" /></NFormItem>
        </NCard>

        <!-- Notifications -->
        <NCard :title="$t('page.settings.emailNotifications')" size="small">
          <NFormItem :label="$t('page.settings.emailNotifications')"><NSwitch v-model:value="localSettings.notifications.email_enabled" /></NFormItem>
          <NFormItem :label="$t('page.settings.adminEmail')"><NInput v-model:value="localSettings.notifications.admin_email" type="text" /></NFormItem>
          <NFormItem :label="$t('page.settings.orderAlerts')"><NSwitch v-model:value="localSettings.notifications.order_alerts" /></NFormItem>
        </NCard>
      </div>
    </NSpin>

    <div v-if="saveMsg" class="text-sm p-2 rounded" :class="saveError ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'">
      {{ saveMsg }}
    </div>

    <div class="flex justify-end">
      <NButton type="primary" :loading="saving" @click="saveAll">{{ $t('page.settings.saveAllSettings') }}</NButton>
    </div>
  </div>
</template>
