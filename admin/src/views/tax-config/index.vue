<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  NAlert,
  NButton,
  NCard,
  NDivider,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NSpin,
  NSwitch,
  NTag,
  NText
} from 'naive-ui';
import { useI18n } from 'vue-i18n';
import {
  fetchTaxConfig,
  previewTax,
  saveTaxConfig,
  type TaxConfig,
  type TaxPreviewResponse,
  type TaxProviderOption,
  type TaxRuleItem
} from '@/service/api/payment';

const { t } = useI18n();

const loading = ref(true);
const saving = ref(false);
const previewing = ref(false);
const note = ref('');
const providers = ref<TaxProviderOption[]>([]);
const defaults = ref<TaxRuleItem[]>([]);
const preview = ref<TaxPreviewResponse | null>(null);

const form = reactive<TaxConfig>({
  provider: 'static',
  enabled: true,
  prices_include_tax: false,
  default_rate: '0',
  rates: []
});

const previewForm = reactive({
  country: 'US',
  region: '',
  category: '',
  amount: 100,
  shipping: 0
});

const providerOptions = computed(() =>
  providers.value.map(item => ({
    label: item.available ? item.label : `${item.label} (${t('page.taxConfig.unavailable')})`,
    value: item.value,
    disabled: !item.available
  }))
);

const currentProvider = computed(() =>
  providers.value.find(item => item.value === form.provider) ?? null
);

function unwrap<T>(res: any): T | null {
  if (res?.error) return null;
  const data = res?.data?.data ?? res?.data ?? res;
  return data && typeof data === 'object' ? (data as T) : null;
}

function applyConfig(config: TaxConfig) {
  form.provider = config.provider ?? 'static';
  form.enabled = config.enabled ?? true;
  form.prices_include_tax = config.prices_include_tax ?? false;
  form.default_rate = String(config.default_rate ?? '0');
  form.rates = (config.rates ?? []).map(rule => ({
    country: rule.country ?? '',
    region: rule.region ?? '',
    category: rule.category ?? '',
    rate: String(rule.rate ?? '0'),
    name: rule.name ?? '',
    applies_to_shipping: !!rule.applies_to_shipping
  }));
}

async function load() {
  loading.value = true;
  const data = unwrap<{
    config: TaxConfig;
    providers: TaxProviderOption[];
    defaults: TaxRuleItem[];
    note: string;
  }>(await fetchTaxConfig());
  if (data) {
    applyConfig(data.config);
    providers.value = data.providers ?? [];
    defaults.value = data.defaults ?? [];
    note.value = data.note ?? '';
  } else {
    window.$message?.error(t('page.taxConfig.loadFail'));
  }
  loading.value = false;
}

function addRule() {
  form.rates.push({
    country: '',
    region: '',
    category: '',
    rate: '0',
    name: '',
    applies_to_shipping: false
  });
}

function removeRule(index: number) {
  form.rates.splice(index, 1);
}

function restoreDefaults() {
  form.rates = defaults.value.map(rule => ({
    country: rule.country ?? '',
    region: rule.region ?? '',
    category: rule.category ?? '',
    rate: String(rule.rate ?? '0'),
    name: rule.name ?? '',
    applies_to_shipping: !!rule.applies_to_shipping
  }));
  window.$message?.success(t('page.taxConfig.defaultsLoaded'));
}

function validate(): string | null {
  for (const [index, rule] of form.rates.entries()) {
    const rate = Number(rule.rate);
    if (Number.isNaN(rate) || rate < 0 || rate > 1) {
      return t('page.taxConfig.rateInvalid', { index: index + 1 });
    }
    if (!rule.country && !rule.category) {
      return t('page.taxConfig.ruleIncomplete', { index: index + 1 });
    }
  }
  const fallback = Number(form.default_rate);
  if (Number.isNaN(fallback) || fallback < 0 || fallback > 1) {
    return t('page.taxConfig.defaultRateInvalid');
  }
  return null;
}

async function onSave() {
  const error = validate();
  if (error) {
    window.$message?.warning(error);
    return;
  }
  saving.value = true;
  const payload: TaxConfig = {
    provider: form.provider,
    enabled: form.enabled,
    prices_include_tax: form.prices_include_tax,
    default_rate: String(form.default_rate),
    rates: form.rates.map(rule => ({
      country: (rule.country || '').trim().toUpperCase(),
      region: (rule.region || '').trim(),
      category: (rule.category || '').trim(),
      rate: String(rule.rate),
      name: (rule.name || '').trim(),
      applies_to_shipping: !!rule.applies_to_shipping
    }))
  };
  const data = unwrap<{ config: TaxConfig }>(await saveTaxConfig(payload));
  saving.value = false;
  if (data) {
    applyConfig(data.config);
    window.$message?.success(t('page.taxConfig.saved'));
  } else {
    window.$message?.error(t('page.taxConfig.saveFail'));
  }
}

async function onPreview() {
  previewing.value = true;
  const data = unwrap<TaxPreviewResponse>(
    await previewTax({
      country: previewForm.country.trim().toUpperCase(),
      region: previewForm.region.trim() || null,
      category: previewForm.category.trim() || null,
      amount: String(previewForm.amount ?? 0),
      shipping: String(previewForm.shipping ?? 0)
    })
  );
  previewing.value = false;
  if (data) preview.value = data;
  else window.$message?.error(t('page.taxConfig.previewFail'));
}

onMounted(load);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">{{ t('page.taxConfig.title') }}</h2>
        <p class="mt-1 text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <NButton size="small" :loading="loading" @click="load">{{ t('page.taxConfig.refresh') }}</NButton>
        <NButton size="small" type="primary" :loading="saving" @click="onSave">
          {{ t('page.taxConfig.save') }}
        </NButton>
      </div>
    </div>

    <NAlert v-if="note" type="info" :bordered="false" :show-icon="true">{{ note }}</NAlert>

    <NSpin :show="loading">
      <div class="flex flex-col gap-4">
        <NCard size="small" :title="t('page.taxConfig.engineTitle')">
          <div class="grid grid-cols-1 gap-x-6 gap-y-2 md:grid-cols-2">
            <NFormItem :label="t('page.taxConfig.enabled')">
              <div class="flex items-center gap-2">
                <NSwitch v-model:value="form.enabled" />
                <span class="text-xs text-[var(--n-text-color-3)]">
                  {{ t('page.taxConfig.enabledHint') }}
                </span>
              </div>
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.provider')">
              <NSelect v-model:value="form.provider" :options="providerOptions" />
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.pricesIncludeTax')">
              <div class="flex items-center gap-2">
                <NSwitch v-model:value="form.prices_include_tax" />
                <span class="text-xs text-[var(--n-text-color-3)]">
                  {{
                    form.prices_include_tax
                      ? t('page.taxConfig.priceInclusive')
                      : t('page.taxConfig.priceExclusive')
                  }}
                </span>
              </div>
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.defaultRate')">
              <NInput v-model:value="form.default_rate" :placeholder="t('page.taxConfig.ratePlaceholder')" />
            </NFormItem>
          </div>
          <p v-if="currentProvider?.description" class="text-xs text-[var(--n-text-color-3)]">
            {{ currentProvider.description }}
          </p>
        </NCard>

        <NCard size="small">
          <template #header>
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ t('page.taxConfig.rulesTitle') }}</span>
              <NTag size="tiny" :bordered="false">{{ form.rates.length }}</NTag>
            </div>
          </template>
          <template #header-extra>
            <div class="flex items-center gap-2">
              <NButton size="tiny" @click="restoreDefaults">{{ t('page.taxConfig.restoreDefaults') }}</NButton>
              <NButton size="tiny" type="primary" @click="addRule">{{ t('page.taxConfig.addRule') }}</NButton>
            </div>
          </template>

          <div class="overflow-x-auto">
            <table class="w-full min-w-[880px] border-collapse text-sm">
              <thead>
                <tr class="text-left text-xs text-[var(--n-text-color-3)]">
                  <th class="w-24 px-2 py-2">{{ t('page.taxConfig.colCountry') }}</th>
                  <th class="w-32 px-2 py-2">{{ t('page.taxConfig.colRegion') }}</th>
                  <th class="w-32 px-2 py-2">{{ t('page.taxConfig.colCategory') }}</th>
                  <th class="w-24 px-2 py-2">{{ t('page.taxConfig.colRate') }}</th>
                  <th class="px-2 py-2">{{ t('page.taxConfig.colName') }}</th>
                  <th class="w-28 px-2 py-2 text-center">{{ t('page.taxConfig.colShipping') }}</th>
                  <th class="w-16 px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="(rule, index) in form.rates" :key="index" class="border-t border-[var(--n-border-color)]">
                  <td class="px-2 py-1">
                    <NInput v-model:value="rule.country" size="small" placeholder="US" />
                  </td>
                  <td class="px-2 py-1">
                    <NInput v-model:value="rule.region" size="small" :placeholder="t('page.taxConfig.regionPlaceholder')" />
                  </td>
                  <td class="px-2 py-1">
                    <NInput v-model:value="rule.category" size="small" :placeholder="t('page.taxConfig.categoryPlaceholder')" />
                  </td>
                  <td class="px-2 py-1">
                    <NInput v-model:value="rule.rate" size="small" placeholder="0.08" />
                  </td>
                  <td class="px-2 py-1">
                    <NInput v-model:value="rule.name" size="small" :placeholder="t('page.taxConfig.namePlaceholder')" />
                  </td>
                  <td class="px-2 py-1 text-center">
                    <NSwitch v-model:value="rule.applies_to_shipping" size="small" />
                  </td>
                  <td class="px-2 py-1 text-center">
                    <NButton text size="tiny" type="error" @click="removeRule(index)">
                      {{ t('page.taxConfig.remove') }}
                    </NButton>
                  </td>
                </tr>
                <tr v-if="!form.rates.length">
                  <td colspan="7" class="px-2 py-6 text-center text-xs text-[var(--n-text-color-3)]">
                    {{ t('page.taxConfig.emptyRules') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="mt-2 text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.ruleHint') }}</p>
        </NCard>

        <NCard size="small" :title="t('page.taxConfig.previewTitle')">
          <div class="grid grid-cols-1 gap-x-4 md:grid-cols-5">
            <NFormItem :label="t('page.taxConfig.colCountry')">
              <NInput v-model:value="previewForm.country" placeholder="US" />
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.colRegion')">
              <NInput v-model:value="previewForm.region" :placeholder="t('page.taxConfig.regionPlaceholder')" />
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.colCategory')">
              <NInput v-model:value="previewForm.category" :placeholder="t('page.taxConfig.categoryPlaceholder')" />
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.previewAmount')">
              <NInputNumber v-model:value="previewForm.amount" :min="0" class="w-full" />
            </NFormItem>
            <NFormItem :label="t('page.taxConfig.previewShipping')">
              <NInputNumber v-model:value="previewForm.shipping" :min="0" class="w-full" />
            </NFormItem>
          </div>
          <div class="flex items-center gap-3">
            <NButton size="small" :loading="previewing" @click="onPreview">
              {{ t('page.taxConfig.preview') }}
            </NButton>
            <NText depth="3" class="text-xs">{{ t('page.taxConfig.previewHint') }}</NText>
          </div>

          <NDivider class="!my-3" />
          <div v-if="preview" class="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div>
              <div class="text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.previewTax') }}</div>
              <div class="font-medium">{{ preview.tax.toFixed(2) }}</div>
            </div>
            <div>
              <div class="text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.previewRate') }}</div>
              <div class="font-medium">{{ (preview.rate * 100).toFixed(2) }}%</div>
            </div>
            <div>
              <div class="text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.previewJurisdiction') }}</div>
              <div class="font-medium">{{ preview.jurisdiction || '-' }}</div>
            </div>
            <div>
              <div class="text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.previewTotal') }}</div>
              <div class="font-medium">{{ preview.total.toFixed(2) }}</div>
            </div>
            <div class="col-span-2 md:col-span-4 text-xs text-[var(--n-text-color-3)]">
              {{ preview.label || preview.name || '-' }}
              ·
              {{ preview.inclusive ? t('page.taxConfig.priceInclusive') : t('page.taxConfig.priceExclusive') }}
            </div>
          </div>
          <p v-else class="text-xs text-[var(--n-text-color-3)]">{{ t('page.taxConfig.previewEmpty') }}</p>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>
