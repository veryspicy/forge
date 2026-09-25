<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  NButton,
  NCard,
  NFormItem,
  NGi,
  NGrid,
  NInput,
  NInputNumber,
  NSelect,
  NSwitch,
  NTag
} from 'naive-ui';
import { get, post, put } from '@/service/api/helper';

interface AIConfigView {
  base_url: string;
  model: string;
  temperature: number;
  max_tokens: number;
  enabled: boolean;
  api_key_masked: string;
  api_key_set: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

interface LLMTestResult {
  status: 'ok' | 'fail';
  latency_ms: number;
  detail: string;
  models_count: number;
  chat_ok: boolean;
  reply: string;
}

const CONFIG_URL = '/api/admin/v1/ai-config';

const loading = ref(true);
const saving = ref(false);
const testing = ref(false);
const loadingModels = ref(false);
const message = ref('');
const messageError = ref(false);

const form = reactive({
  base_url: '',
  api_key: '',
  model: '',
  temperature: 0.7,
  max_tokens: 1024,
  enabled: true
});

const apiKeySet = ref(false);
const apiKeyMasked = ref('');
const updatedInfo = ref('');
const testResult = ref<LLMTestResult | null>(null);
const modelOptions = ref<{ label: string; value: string }[]>([]);

const testTagType = computed(() => (testResult.value?.status === 'ok' ? 'success' : 'error'));

function showMessage(text: string, isError = false) {
  message.value = text;
  messageError.value = isError;
}

/**
 * 解包后端响应：admin 接口统一返回 { data: payload }，
 * request 封装的 transform 已透出整个响应体，故业务载荷位于 res.data.data。
 * 兼容裸载荷（res.data 直接为 payload）以避免后端包裹变化时页面再次失效。
 */
function unwrap<T>(res: any): T {
  return (res?.data?.data ?? res?.data ?? res ?? {}) as T;
}

function buildPayload() {
  return {
    base_url: form.base_url,
    // 空字符串表示保留服务端已保存的密钥，避免脱敏串覆盖真实 key
    api_key: form.api_key,
    model: form.model,
    temperature: form.temperature,
    max_tokens: form.max_tokens,
    enabled: form.enabled
  };
}

async function loadConfig() {
  loading.value = true;
  try {
    const res = await get<AIConfigView>(`${CONFIG_URL}/config`);
    const data = unwrap<AIConfigView>(res);
    form.base_url = data.base_url ?? '';
    form.model = data.model ?? '';
    form.temperature = data.temperature ?? 0.7;
    form.max_tokens = data.max_tokens ?? 1024;
    form.enabled = data.enabled ?? true;
    form.api_key = '';
    apiKeySet.value = Boolean(data.api_key_set);
    apiKeyMasked.value = data.api_key_masked ?? '';
    updatedInfo.value = data.updated_at
      ? `${data.updated_at}${data.updated_by ? ` · ${data.updated_by}` : ''}`
      : '';
    if (form.model) {
      modelOptions.value = [{ label: form.model, value: form.model }];
    }
  } catch (e: any) {
    showMessage(e?.response?.data?.detail || (e?.message ?? 'load failed'), true);
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  saving.value = true;
  try {
    await put(`${CONFIG_URL}/config`, buildPayload());
    showMessage('saved');
    await loadConfig();
  } catch (e: any) {
    showMessage(e?.response?.data?.detail || (e?.message ?? 'save failed'), true);
  } finally {
    saving.value = false;
  }
}

async function testConnection() {
  testing.value = true;
  testResult.value = null;
  try {
    const res = await post<LLMTestResult>(`${CONFIG_URL}/test`, buildPayload());
    const data = unwrap<LLMTestResult>(res);
    testResult.value =
      data?.status
        ? data
        : ({ status: 'fail', latency_ms: 0, detail: 'empty response', models_count: 0, chat_ok: false, reply: '' } as LLMTestResult);
  } catch (e: any) {
    testResult.value = {
      status: 'fail',
      latency_ms: 0,
      detail: e?.response?.data?.detail || e?.message || 'request failed',
      models_count: 0,
      chat_ok: false,
      reply: ''
    };
  } finally {
    testing.value = false;
  }
}

async function fetchModels() {
  loadingModels.value = true;
  try {
    const res = await post<{ models: string[]; count: number }>(`${CONFIG_URL}/models`, buildPayload());
    const payload = unwrap<{ models: string[]; count: number }>(res);
    const list = payload?.models ?? [];
    modelOptions.value = list.map(id => ({ label: id, value: id }));
    showMessage(`models: ${payload?.count ?? list.length}`);
    if (!form.model && list.length) {
      form.model = list[0];
    }
  } catch (e: any) {
    showMessage(e?.response?.data?.detail || e?.message || 'fetch models failed', true);
  } finally {
    loadingModels.value = false;
  }
}

onMounted(loadConfig);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold">{{ $t('page.aiConfig.title') }}</h2>
      <span v-if="updatedInfo" class="text-xs text-[var(--n-text-color-3)]">
        {{ $t('page.aiConfig.lastUpdated') }}: {{ updatedInfo }}
      </span>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <!-- LLM connection -->
      <NCard :title="$t('page.aiConfig.llmConfig')" size="small" class="md:col-span-2">
        <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
          <NGi span="1">
            <NFormItem :label="$t('page.aiConfig.baseUrl')">
              <NInput v-model:value="form.base_url" placeholder="https://integrate.api.nvidia.com/v1" />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.aiConfig.apiKey')">
              <NInput
                v-model:value="form.api_key"
                type="password"
                show-password-on="click"
                :placeholder="apiKeySet ? apiKeyMasked : $t('page.aiConfig.apiKeyPlaceholder')"
              />
            </NFormItem>
            <div class="mb-3 flex items-center gap-2">
              <NTag :type="apiKeySet ? 'success' : 'warning'" size="small">
                {{ apiKeySet ? $t('page.aiConfig.apiKeyConfigured') : $t('page.aiConfig.apiKeyNotConfigured') }}
              </NTag>
              <span class="text-xs text-[var(--n-text-color-3)]">{{ $t('page.aiConfig.apiKeyHint') }}</span>
            </div>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.aiConfig.enabled')">
              <NSwitch v-model:value="form.enabled" />
            </NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Model selection -->
      <NCard :title="$t('page.aiConfig.modelSection')" size="small">
        <NFormItem :label="$t('page.aiConfig.model')">
          <NSelect
            v-model:value="form.model"
            :options="modelOptions"
            filterable
            tag
            :placeholder="$t('page.aiConfig.modelPlaceholder')"
          />
        </NFormItem>
        <NButton size="small" :loading="loadingModels" @click="fetchModels">
          {{ $t('page.aiConfig.fetchModels') }}
        </NButton>
      </NCard>

      <!-- Generation params -->
      <NCard :title="$t('page.aiConfig.paramSection')" size="small">
        <NFormItem :label="$t('page.aiConfig.temperature')">
          <NInputNumber v-model:value="form.temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
        </NFormItem>
        <NFormItem :label="$t('page.aiConfig.maxTokens')">
          <NInputNumber v-model:value="form.max_tokens" :min="1" :max="32768" style="width: 100%" />
        </NFormItem>
      </NCard>

      <!-- Test result -->
      <NCard v-if="testResult" :title="$t('page.aiConfig.testResult')" size="small" class="md:col-span-2">
        <div class="flex flex-col gap-2">
          <div class="flex items-center gap-3">
            <NTag :type="testTagType" size="small">
              {{ testResult.status === 'ok' ? $t('page.aiConfig.testOk') : $t('page.aiConfig.testFail') }}
            </NTag>
            <span class="text-xs text-[var(--n-text-color-3)]">{{ testResult.latency_ms }} ms</span>
            <span class="text-xs text-[var(--n-text-color-3)]">
              {{ $t('page.aiConfig.upstreamModels') }}: {{ testResult.models_count }}
            </span>
            <NTag :type="testResult.chat_ok ? 'success' : 'warning'" size="small">
              {{ testResult.chat_ok ? $t('page.aiConfig.chatOk') : $t('page.aiConfig.chatFail') }}
            </NTag>
          </div>
          <p class="text-sm break-all text-[var(--n-text-color-3)]">{{ testResult.detail }}</p>
          <p v-if="testResult.reply" class="text-sm break-all">
            <b>{{ $t('page.aiConfig.reply') }}:</b> {{ testResult.reply }}
          </p>
        </div>
      </NCard>
    </div>

    <div
      v-if="message"
      class="rounded p-2 text-sm"
      :class="messageError ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'"
    >
      {{ message }}
    </div>

    <div class="flex justify-end gap-3">
      <NButton :loading="testing" @click="testConnection">{{ $t('page.aiConfig.test') }}</NButton>
      <NButton type="primary" :loading="saving" @click="saveConfig">{{ $t('page.aiConfig.save') }}</NButton>
    </div>
  </div>
</template>
