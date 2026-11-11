<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  NAlert,
  NButton,
  NCard,
  NDivider,
  NEmpty,
  NFormItem,
  NInput,
  NSelect,
  NSpin,
  NSwitch,
  NTag,
  NTooltip
} from 'naive-ui';
import { useI18n } from 'vue-i18n';
import {
  CLEAR_SENTINEL,
  fetchPaymentConfig,
  savePaymentChannelCredentials,
  testPaymentChannel,
  togglePaymentChannel,
  type PaymentChannelField,
  type PaymentChannelState
} from '@/service/api/payment';

const { t } = useI18n();

const loading = ref(true);
const note = ref('');
const channels = ref<PaymentChannelState[]>([]);
const formValues = reactive<Record<string, Record<string, string>>>({});
const clearing = reactive<Record<string, boolean>>({});
const savingChannel = ref('');
const testingChannel = ref('');
const testResults = reactive<Record<string, { ok: boolean; message: string }>>({});

const enabledCount = computed(() => channels.value.filter(item => item.enabled).length);

function unwrap<T>(res: any): T | null {
  if (res?.error) return null;
  const data = res?.data?.data ?? res?.data ?? res;
  return data && typeof data === 'object' ? (data as T) : null;
}

function resetForm(channel: PaymentChannelState) {
  const values: Record<string, string> = {};
  channel.fields.forEach(field => {
    values[field.key] = '';
  });
  formValues[channel.channel] = values;
  clearing[channel.channel] = false;
}

function applyChannels(list: PaymentChannelState[]) {
  channels.value = list ?? [];
  channels.value.forEach(item => {
    if (!formValues[item.channel]) resetForm(item);
  });
}

async function load() {
  loading.value = true;
  const data = unwrap<{ channels: PaymentChannelState[]; note: string }>(await fetchPaymentConfig());
  if (data) {
    applyChannels(data.channels);
    note.value = data.note ?? '';
  } else {
    window.$message?.error(t('page.paymentConfig.loadFail'));
  }
  loading.value = false;
}

async function reloadOne(channel: string) {
  const data = unwrap<{ channels: PaymentChannelState[] }>(await fetchPaymentConfig());
  if (data) {
    channels.value = data.channels ?? [];
  }
  const target = channels.value.find(item => item.channel === channel);
  if (target) resetForm(target);
}

async function onToggle(item: PaymentChannelState, value: boolean) {
  const data = unwrap<{ enabled: boolean; enabled_channels: string[] }>(
    await togglePaymentChannel(item.channel, value)
  );
  if (data) {
    window.$message?.success(t('page.paymentConfig.saved'));
    item.enabled = data.enabled;
  } else {
    window.$message?.error(t('page.paymentConfig.saveFail'));
    await reloadOne(item.channel);
  }
}

function fieldModel(channel: string, key: string) {
  if (!formValues[channel]) formValues[channel] = {};
  if (formValues[channel][key] === undefined) formValues[channel][key] = '';
  return formValues[channel][key];
}

function setField(channel: string, key: string, value: string) {
  if (!formValues[channel]) formValues[channel] = {};
  formValues[channel][key] = value;
}

function markClear(item: PaymentChannelState, field: PaymentChannelField, value: boolean) {
  clearing[`${item.channel}.${field.key}`] = value;
  if (value) setField(item.channel, field.key, '');
}

async function onSave(item: PaymentChannelState) {
  const values: Record<string, string> = {};
  item.fields.forEach(field => {
    const raw = (formValues[item.channel]?.[field.key] ?? '').trim();
    if (clearing[`${item.channel}.${field.key}`]) {
      if (field.type === 'secret') values[field.key] = CLEAR_SENTINEL;
      return;
    }
    if (raw) values[field.key] = raw;
  });
  if (!Object.keys(values).length) {
    window.$message?.warning(t('page.paymentConfig.nothingToSave'));
    return;
  }
  savingChannel.value = item.channel;
  const data = unwrap<{ config: PaymentChannelState }>(
    await savePaymentChannelCredentials(item.channel, values)
  );
  savingChannel.value = '';
  if (data) {
    window.$message?.success(t('page.paymentConfig.saved'));
    if (data.config) {
      const index = channels.value.findIndex(entry => entry.channel === data.config.channel);
      if (index >= 0) channels.value[index] = data.config;
      resetForm(data.config);
    }
  } else {
    window.$message?.error(t('page.paymentConfig.saveFail'));
  }
}

async function onTest(item: PaymentChannelState) {
  testingChannel.value = item.channel;
  const data = unwrap<{ ok: boolean; message: string }>(await testPaymentChannel(item.channel));
  testingChannel.value = '';
  if (data) {
    testResults[item.channel] = { ok: !!data.ok, message: data.message ?? '' };
  } else {
    testResults[item.channel] = { ok: false, message: t('page.paymentConfig.testFail') };
  }
}

onMounted(load);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">{{ t('page.paymentConfig.title') }}</h2>
        <p class="mt-1 text-xs text-[var(--n-text-color-3)]">{{ t('page.paymentConfig.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <NTag size="small" :bordered="false" type="info">
          {{ t('page.paymentConfig.enabledCount', { count: enabledCount }) }}
        </NTag>
        <NButton size="small" :loading="loading" @click="load">{{ t('page.paymentConfig.refresh') }}</NButton>
      </div>
    </div>

    <NAlert v-if="note" type="info" :bordered="false" :show-icon="true">{{ note }}</NAlert>
    <NAlert v-if="!loading && channels.length && !enabledCount" type="warning" :show-icon="true">
      {{ t('page.paymentConfig.atLeastOne') }}
    </NAlert>

    <NSpin :show="loading">
      <NEmpty v-if="!loading && !channels.length" :description="t('page.paymentConfig.empty')" />
      <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <NCard v-for="item in channels" :key="item.channel" size="small">
          <template #header>
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ item.name || item.channel }}</span>
              <NTag size="tiny" :bordered="false" :type="item.configured ? 'success' : 'warning'">
                {{
                  item.configured
                    ? t('page.paymentConfig.configured')
                    : t('page.paymentConfig.notConfigured')
                }}
              </NTag>
              <NTag v-if="item.enabled" size="tiny" type="success" :bordered="false">
                {{ t('page.paymentConfig.enabledLabel') }}
              </NTag>
              <NTag v-else size="tiny" :bordered="false">{{ t('page.paymentConfig.disabledLabel') }}</NTag>
            </div>
          </template>
          <template #header-extra>
            <div class="flex items-center gap-2">
              <span class="text-xs text-[var(--n-text-color-3)]">{{ item.channel }}</span>
              <NSwitch
                size="small"
                :value="item.enabled"
                @update:value="(value: boolean) => onToggle(item, value)"
              />
            </div>
          </template>

          <p v-if="item.description" class="mb-2 text-xs text-[var(--n-text-color-3)]">
            {{ item.description }}
          </p>

          <div class="grid grid-cols-1 gap-x-4 md:grid-cols-2">
            <NFormItem
              v-for="field in item.fields"
              :key="field.key"
              :label="field.label"
              :required="field.required"
            >
              <div class="w-full">
                <NSelect
                  v-if="field.type === 'select'"
                  :value="fieldModel(item.channel, field.key) || field.value || null"
                  :options="field.options"
                  :placeholder="field.placeholder"
                  clearable
                  @update:value="(value: string | null) => setField(item.channel, field.key, value ?? '')"
                />
                <NInput
                  v-else
                  :value="fieldModel(item.channel, field.key)"
                  :type="field.type === 'secret' ? 'password' : 'text'"
                  show-password-on="click"
                  :placeholder="
                    field.saved && field.type === 'secret'
                      ? t('page.paymentConfig.secretKeepHint', { masked: field.masked || '******' })
                      : field.placeholder
                  "
                  :disabled="clearing[`${item.channel}.${field.key}`]"
                  @update:value="(value: string) => setField(item.channel, field.key, value)"
                />
                <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--n-text-color-3)]">
                  <NTag v-if="field.saved && field.type === 'secret'" size="tiny" :bordered="false" type="success">
                    {{ t('page.paymentConfig.secretSaved', { masked: field.masked || '******' }) }}
                  </NTag>
                  <NTooltip v-if="field.help_text" trigger="hover">
                    <template #trigger>
                      <span class="cursor-help underline decoration-dotted">{{ t('page.paymentConfig.help') }}</span>
                    </template>
                    {{ field.help_text }}
                  </NTooltip>
                  <NButton
                    v-if="field.saved && field.type === 'secret'"
                    text
                    size="tiny"
                    type="error"
                    @click="markClear(item, field, !clearing[`${item.channel}.${field.key}`])"
                  >
                    {{
                      clearing[`${item.channel}.${field.key}`]
                        ? t('page.paymentConfig.cancelClear')
                        : t('page.paymentConfig.clearSaved')
                    }}
                  </NButton>
                </div>
              </div>
            </NFormItem>
          </div>

          <NDivider class="!my-2" />

          <div class="flex flex-wrap items-center gap-3">
            <NButton
              size="small"
              type="primary"
              :loading="savingChannel === item.channel"
              @click="onSave(item)"
            >
              {{ t('page.paymentConfig.save') }}
            </NButton>
            <NButton
              size="small"
              :loading="testingChannel === item.channel"
              :disabled="!item.configured"
              @click="onTest(item)"
            >
              {{ t('page.paymentConfig.test') }}
            </NButton>
            <a
              v-if="item.docs_url"
              class="text-xs text-[var(--n-text-color-3)] underline"
              :href="item.docs_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ t('page.paymentConfig.docs') }}
            </a>
          </div>

          <NAlert
            v-if="testResults[item.channel]"
            class="mt-3"
            :type="testResults[item.channel].ok ? 'success' : 'error'"
            :bordered="false"
          >
            {{ testResults[item.channel].message || t('page.paymentConfig.testDone') }}
          </NAlert>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>
