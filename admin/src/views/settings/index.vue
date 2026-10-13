<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { NButton, NCard, NFormItem, NGi, NGrid, NInput, NInputNumber, NSelect, NSpin, NSwitch } from 'naive-ui';
import { get, put } from '@/service/api/helper';

const loading = ref(true);
const saving = ref(false);
const saveMsg = ref('');
const saveError = ref(false);

const localSettings = reactive({
  store_name: 'Forge',
  currency: 'USD',
  region: 'AE',
  language: 'en',
  product_audit_enabled: false,
  trust_badges: {
    free_shipping: { enabled: true, threshold: 50 },
    returns: { enabled: true, days: 30 },
    secure_checkout: { enabled: true }
  },
  order_settings: {
    auto_review: false,
    max_items_per_order: 10,
    default_currency: 'USD',
    order_prefix: 'PAI',
    expiry_hours: 24
  },
  notifications: { email_enabled: true, admin_email: '', order_alerts: true }
});

const currencyOptions = [
  { label: 'USD', value: 'USD' },
  { label: 'AED', value: 'AED' },
  { label: 'SAR', value: 'SAR' }
];
const regionOptions = ['AE', 'SA', 'KW', 'QA', 'OM', 'BH'].map(v => ({ label: v, value: v }));
const langOptions = [
  { label: 'English', value: 'en' },
  { label: 'Arabic', value: 'ar' }
];

async function loadSettings() {
  try {
    const res = await get('/api/admin/v1/settings/');
    if (res.data && Object.keys(res.data).length) {
      Object.assign(localSettings, res.data);
      localSettings.order_settings = {
        auto_review: false,
        max_items_per_order: 10,
        default_currency: 'USD',
        order_prefix: 'PAI',
        expiry_hours: 24,
        ...res.data.order_settings
      };
      localSettings.notifications = {
        email_enabled: true,
        admin_email: '',
        order_alerts: true,
        ...res.data.notifications
      };
      localSettings.trust_badges = {
        free_shipping: { enabled: true, threshold: 50, ...res.data.trust_badges?.free_shipping },
        returns: { enabled: true, days: 30, ...res.data.trust_badges?.returns },
        secure_checkout: { enabled: true, ...res.data.trust_badges?.secure_checkout }
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
        <!-- Store Settings -->
        <NCard :title="$t('page.settings.storeSettings')" size="small" class="md:col-span-2">
          <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
            <NGi span="1">
              <NFormItem :label="$t('page.settings.storeName')">
                <NInput v-model:value="localSettings.store_name" />
              </NFormItem>
            </NGi>
            <NGi span="1">
              <NFormItem :label="$t('page.settings.defaultCurrency')">
                <NSelect v-model:value="localSettings.currency" :options="currencyOptions" />
              </NFormItem>
            </NGi>
            <NGi span="1">
              <NFormItem :label="$t('common.region')">
                <NSelect v-model:value="localSettings.region" :options="regionOptions" />
              </NFormItem>
            </NGi>
            <NGi span="1">
              <NFormItem :label="$t('common.language')">
                <NSelect v-model:value="localSettings.language" :options="langOptions" />
              </NFormItem>
            </NGi>
          </NGrid>

          <!-- Trust Badges（店铺级信任标识配置，随站点配置保存） -->
          <div class="mt-4 border-t pt-4">
            <div class="mb-3 text-sm font-medium">Trust Badges</div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-2">
                <div class="flex h-8 items-center justify-between">
                  <span class="text-sm">Free Shipping</span>
                  <NSwitch v-model:value="localSettings.trust_badges.free_shipping.enabled" />
                </div>
                <NFormItem label="免邮阈值 ($)">
                  <NInputNumber
                    v-model:value="localSettings.trust_badges.free_shipping.threshold"
                    :min="0"
                    style="width: 100%"
                  />
                </NFormItem>
              </div>
              <div class="flex flex-col gap-2">
                <div class="flex h-8 items-center justify-between">
                  <span class="text-sm">Returns</span>
                  <NSwitch v-model:value="localSettings.trust_badges.returns.enabled" />
                </div>
                <NFormItem label="退换天数">
                  <NInputNumber
                    v-model:value="localSettings.trust_badges.returns.days"
                    :min="0"
                    style="width: 100%"
                  />
                </NFormItem>
              </div>
              <div class="flex flex-col gap-2">
                <div class="flex h-8 items-center justify-between">
                  <span class="text-sm">Secure Checkout</span>
                  <NSwitch v-model:value="localSettings.trust_badges.secure_checkout.enabled" />
                </div>
                <NFormItem label=" ">
                  <div class="h-8" aria-hidden="true"></div>
                </NFormItem>
              </div>
            </div>
          </div>
        </NCard>

        <!-- Order Settings -->
        <NCard :title="$t('page.settings.orderSettings')" size="small">
          <NFormItem :label="$t('page.settings.autoReview')">
            <NSwitch v-model:value="localSettings.order_settings.auto_review" />
          </NFormItem>
          <NFormItem :label="$t('page.settings.maxItemsPerOrder')">
            <NInputNumber
              v-model:value="localSettings.order_settings.max_items_per_order"
              :min="1"
              style="width: 100%"
            />
          </NFormItem>
          <NFormItem :label="$t('page.settings.defaultCurrency')">
            <NSelect v-model:value="localSettings.order_settings.default_currency" :options="currencyOptions" />
          </NFormItem>
          <NFormItem :label="$t('page.settings.orderPrefix')">
            <NInput v-model:value="localSettings.order_settings.order_prefix" />
          </NFormItem>
          <NFormItem :label="$t('page.settings.expiryHours')">
            <NInputNumber v-model:value="localSettings.order_settings.expiry_hours" :min="1" style="width: 100%" />
          </NFormItem>
        </NCard>

        <!-- Product Audit Switch（PRODUCT-AUDIT-FLOW 开关化） -->
        <NCard title="商品审核" size="small" class="md:col-span-2">
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-500">启用商品发布审核流程（默认关闭，对齐自营单商家模式）</span>
            <NSwitch v-model:value="localSettings.product_audit_enabled" />
          </div>
        </NCard>

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
