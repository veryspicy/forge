<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  NAlert,
  NButton,
  NCard,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  NSwitch,
  NTag
} from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { useI18n } from 'vue-i18n';
import { del, get, post, put } from '@/service/api/helper';

const { t } = useI18n();

interface ProviderModel {
  id: string;
  context_window: number | null;
  capabilities: string[];
}

interface ProviderUpstream {
  id: string;
  name: string;
  base_url: string;
  protocol: string;
  model: string;
  enabled: boolean;
  api_key?: string;
  api_key_masked?: string;
  api_key_set?: boolean;
}

interface LastTest {
  status?: string;
  latency_ms?: number;
  detail?: string;
  at?: string;
}

interface ProviderView {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  protocol: string;
  base_url: string;
  model: string;
  temperature: number;
  max_tokens: number;
  models: ProviderModel[];
  upstreams: ProviderUpstream[];
  created_at?: string;
  updated_at?: string;
  last_test?: LastTest | null;
  api_key_masked?: string;
  api_key_set?: boolean;
}

interface StoreView {
  items: ProviderView[];
  active_id: string | null;
  enabled: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

interface EndpointResult {
  label: string;
  status: string;
  latency_ms: number;
  detail: string;
  models_count: number;
  chat_ok: boolean;
  reply: string;
}

interface TestResult {
  status: string;
  latency_ms: number;
  detail: string;
  models_count: number;
  chat_ok: boolean;
  reply: string;
  endpoints?: EndpointResult[];
}

const BASE = '/api/admin/v1/ai-config';

const loading = ref(true);
const saving = ref(false);
const importing = ref(false);
const testingIds = ref<string[]>([]);
const cardTests = reactive<Record<string, TestResult>>({});
const modelOptions = ref<{ label: string; value: string }[]>([]);

const store = reactive<StoreView>({
  items: [],
  active_id: null,
  enabled: true,
  updated_at: null,
  updated_by: null
});

const drawer = reactive({
  show: false,
  mode: 'create' as 'create' | 'edit',
  providerId: '',
  loadingModels: false,
  testing: false,
  result: null as TestResult | null
});

const form = reactive({
  name: '',
  type: 'api',
  protocol: 'chat',
  base_url: '',
  api_key: '',
  model: '',
  temperature: 0.7,
  max_tokens: 1024,
  enabled: true,
  models: [] as ProviderModel[],
  upstreams: [] as ProviderUpstream[]
});

const importer = reactive({ show: false, text: '' });

const typeOptions = computed(() => [
  { label: t('page.modelManagement.typeApi'), value: 'api' },
  { label: t('page.modelManagement.typeAggregate'), value: 'aggregate' }
]);

const protocolOptions = computed(() => [
  { label: t('page.modelManagement.protocolChat'), value: 'chat' },
  { label: t('page.modelManagement.protocolResponses'), value: 'responses' }
]);

function typeLabel(type: string) {
  return type === 'aggregate' ? t('page.modelManagement.typeAggregate') : t('page.modelManagement.typeApi');
}

const updatedInfo = computed(() =>
  store.updated_at ? `${store.updated_at}${store.updated_by ? ` · ${store.updated_by}` : ''}` : ''
);

/** 失败提示：只按 data.code 取 errors.* 本地化文案（契约见 docs/ERROR-CODE-CONVENTION.md），禁止直显后端 message/detail。 */
function errorMessage(error: any, fallback: string): string {
  const code = error?.response?.data?.code ?? error?.data?.code;
  if (typeof code === 'string' && code) {
    const key = `errors.${code}` as App.I18n.I18nKey;
    const localized = t(key) as string;
    if (localized && localized !== key) return localized;
  }
  return fallback;
}

/**
 * flat request 响应解包（见 service/request/index.ts）：
 * 请求层失败时不会 reject，失败信息在 res.error 中；此时必须返回 null，
 * 否则把 { data: null, error } 当数据用会把列表清空并误报成功。
 */
function unwrap<T>(res: any): T | null {
  if (res?.error) return null;
  const data = res?.data?.data ?? res?.data ?? res;
  return data && typeof data === 'object' ? (data as T) : null;
}

function applyStore(data: StoreView) {
  store.items = data.items ?? [];
  store.active_id = data.active_id ?? null;
  store.enabled = data.enabled ?? true;
  store.updated_at = data.updated_at ?? null;
  store.updated_by = data.updated_by ?? null;
}

async function loadStore() {
  loading.value = true;
  const data = unwrap<StoreView>(await get<StoreView>(`${BASE}/providers`));
  if (data) applyStore(data);
  loading.value = false;
}

/** 变更类请求：失败返回 null（错误提示由请求层统一弹出），成功后写回本地状态。 */
async function mutateStore(promise: Promise<any>): Promise<StoreView | null> {
  const data = unwrap<StoreView>(await promise);
  if (!data) return null;
  applyStore(data);
  return data;
}

async function toggleStoreEnabled(value: boolean) {
  const data = await mutateStore(put<StoreView>(`${BASE}/enabled`, { enabled: value }));
  if (data) window.$message?.success(t('page.modelManagement.saved'));
  else await loadStore();
}

async function onSortEnd() {
  const provider_ids = store.items.map(item => item.id);
  const data = await mutateStore(post<StoreView>(`${BASE}/providers/reorder`, { provider_ids }));
  if (data) window.$message?.success(t('page.modelManagement.sortSaved'));
  else await loadStore();
}

async function activate(item: ProviderView) {
  const data = await mutateStore(post<StoreView>(`${BASE}/providers/${item.id}/activate`, {}));
  if (data) window.$message?.success(t('page.modelManagement.activated'));
}

async function toggleProvider(item: ProviderView, value: boolean) {
  const data = await mutateStore(put<StoreView>(`${BASE}/providers/${item.id}`, { enabled: value }));
  if (!data) await loadStore();
}

async function duplicate(item: ProviderView) {
  const data = await mutateStore(post<StoreView>(`${BASE}/providers/${item.id}/duplicate`, {}));
  if (data) window.$message?.success(t('page.modelManagement.duplicated'));
}

async function remove(item: ProviderView) {
  const data = await mutateStore(del<StoreView>(`${BASE}/providers/${item.id}`));
  if (data) window.$message?.success(t('page.modelManagement.deleted'));
}

function testFailResult(error: any): TestResult {
  return {
    status: 'fail',
    latency_ms: 0,
    detail: errorMessage(error, t('page.modelManagement.testFail')),
    models_count: 0,
    chat_ok: false,
    reply: ''
  };
}

async function testProvider(item: ProviderView) {
  testingIds.value = [...testingIds.value, item.id];
  const res = await post<TestResult>(`${BASE}/providers/test`, { provider_id: item.id });
  const data = unwrap<TestResult>(res);
  if (data) {
    cardTests[item.id] = data;
    await loadStore();
  } else {
    cardTests[item.id] = testFailResult(res?.error);
  }
  testingIds.value = testingIds.value.filter(id => id !== item.id);
}

function isTesting(id: string) {
  return testingIds.value.includes(id);
}

function openCreate() {
  drawer.mode = 'create';
  drawer.providerId = '';
  drawer.result = null;
  form.name = '';
  form.type = 'api';
  form.protocol = 'chat';
  form.base_url = '';
  form.api_key = '';
  form.model = '';
  form.temperature = 0.7;
  form.max_tokens = 1024;
  form.enabled = true;
  form.models = [];
  form.upstreams = [];
  modelOptions.value = [];
  drawer.show = true;
}

function openEdit(item: ProviderView) {
  drawer.mode = 'edit';
  drawer.providerId = item.id;
  drawer.result = null;
  form.name = item.name ?? '';
  form.type = item.type ?? 'api';
  form.protocol = item.protocol ?? 'chat';
  form.base_url = item.base_url ?? '';
  form.api_key = '';
  form.model = item.model ?? '';
  form.temperature = item.temperature ?? 0.7;
  form.max_tokens = item.max_tokens ?? 1024;
  form.enabled = item.enabled ?? true;
  form.models = (item.models ?? []).map(model => ({
    id: model.id,
    context_window: model.context_window ?? null,
    capabilities: [...(model.capabilities ?? [])]
  }));
  form.upstreams = (item.upstreams ?? []).map(upstream => ({
    id: upstream.id,
    name: upstream.name ?? '',
    base_url: upstream.base_url ?? '',
    protocol: upstream.protocol ?? 'chat',
    model: upstream.model ?? '',
    enabled: upstream.enabled ?? true,
    api_key: '',
    api_key_masked: upstream.api_key_masked,
    api_key_set: upstream.api_key_set
  }));
  modelOptions.value = form.model ? [{ label: form.model, value: form.model }] : [];
  drawer.show = true;
}

function addModel() {
  form.models.push({ id: '', context_window: null, capabilities: [] });
}

function removeModel(index: number) {
  form.models.splice(index, 1);
}

function addUpstream() {
  form.upstreams.push({
    id: '',
    name: t('page.modelManagement.upstreamDefault', { index: form.upstreams.length + 1 }),
    base_url: '',
    protocol: 'chat',
    model: '',
    enabled: true,
    api_key: ''
  });
}

function removeUpstream(index: number) {
  form.upstreams.splice(index, 1);
}

function buildPayload() {
  return {
    name: form.name.trim(),
    type: form.type,
    protocol: form.protocol,
    base_url: form.base_url.trim(),
    api_key: form.api_key,
    model: form.model,
    temperature: form.temperature,
    max_tokens: form.max_tokens,
    enabled: form.enabled,
    models: form.models
      .filter(model => model.id.trim())
      .map(model => ({
        id: model.id.trim(),
        context_window: model.context_window,
        capabilities: model.capabilities
      })),
    upstreams: form.upstreams
      .filter(upstream => upstream.base_url.trim())
      .map(upstream => ({
        id: upstream.id || undefined,
        name: upstream.name,
        base_url: upstream.base_url.trim(),
        protocol: upstream.protocol,
        model: upstream.model,
        api_key: upstream.api_key || '',
        enabled: upstream.enabled
      }))
  };
}

async function save() {
  if (!form.name.trim()) {
    window.$message?.warning(t('page.modelManagement.missingName'));
    return;
  }
  saving.value = true;
  const payload = buildPayload();
  const promise =
    drawer.mode === 'create'
      ? post<StoreView>(`${BASE}/providers`, payload)
      : put<StoreView>(`${BASE}/providers/${drawer.providerId}`, payload);
  const data = await mutateStore(promise);
  if (data) {
    window.$message?.success(t('page.modelManagement.saved'));
    drawer.show = false;
  }
  saving.value = false;
}

async function fetchModels() {
  if (!form.base_url.trim()) {
    window.$message?.warning(t('page.modelManagement.missingBaseUrl'));
    return;
  }
  drawer.loadingModels = true;
  const payload: Record<string, any> = { base_url: form.base_url, api_key: form.api_key };
  if (drawer.mode === 'edit') {
    payload.provider_id = drawer.providerId;
  }
  const data = unwrap<{ models: string[]; count: number }>(await post(`${BASE}/providers/models`, payload));
  if (data) {
    const list = data.models ?? [];
    modelOptions.value = list.map(id => ({ label: id, value: id }));
    window.$message?.success(t('page.modelManagement.modelsFetched', { count: data.count ?? list.length }));
    if (!form.model && list.length) {
      form.model = list[0];
    }
  }
  drawer.loadingModels = false;
}

async function testDraft() {
  drawer.testing = true;
  drawer.result = null;
  const payload: Record<string, any> = { ...buildPayload(), base_url: form.base_url.trim() };
  if (drawer.mode === 'edit') {
    payload.provider_id = drawer.providerId;
  } else {
    payload.name = form.name.trim() || t('page.modelManagement.draftName');
  }
  const res = await post<TestResult>(`${BASE}/providers/test`, payload);
  const data = unwrap<TestResult>(res);
  drawer.result = data ?? testFailResult(res?.error);
  drawer.testing = false;
}

async function submitImport() {
  if (!importer.text.trim()) {
    window.$message?.warning(t('page.modelManagement.importEmpty'));
    return;
  }
  importing.value = true;
  const data = unwrap<{ items: ProviderView[]; imported: number }>(
    await post(`${BASE}/providers/import`, { text: importer.text })
  );
  if (data) {
    const count = data.imported ?? data.items?.length ?? 0;
    if (count) {
      window.$message?.success(t('page.modelManagement.imported', { count }));
      importer.show = false;
      importer.text = '';
      await loadStore();
    } else {
      window.$message?.warning(t('page.modelManagement.importEmpty'));
    }
  }
  importing.value = false;
}

function statusTagType(status?: string) {
  return status === 'ok' ? 'success' : 'error';
}

onMounted(loadStore);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">{{ t('page.modelManagement.title') }}</h2>
        <p class="mt-1 text-xs text-[var(--n-text-color-3)]">{{ t('page.modelManagement.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs text-[var(--n-text-color-3)]">{{ updatedInfo }}</span>
        <span class="text-sm">{{ t('page.modelManagement.enabled') }}</span>
        <NSwitch :value="store.enabled" @update:value="toggleStoreEnabled" />
        <NButton size="small" :loading="importing" @click="importer.show = true">
          {{ t('page.modelManagement.importConfig') }}
        </NButton>
        <NButton size="small" type="primary" @click="openCreate">
          {{ t('page.modelManagement.addProvider') }}
        </NButton>
      </div>
    </div>

    <NAlert v-if="!store.enabled" type="warning" :show-icon="true">
      {{ t('page.modelManagement.disabledHint') }}
    </NAlert>

    <NEmpty v-if="!loading && !store.items.length" :description="t('page.modelManagement.empty')">
      <template #extra>
        <NButton size="small" type="primary" @click="openCreate">
          {{ t('page.modelManagement.addProvider') }}
        </NButton>
      </template>
    </NEmpty>

    <VueDraggable
      v-model="store.items"
      :animation="180"
      handle=".drag-handle"
      class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      @end="onSortEnd"
    >
      <NCard
        v-for="item in store.items"
        :key="item.id"
        size="small"
        :class="item.id === store.active_id ? 'shadow-[0_0_0_2px_#18a058]' : ''"
      >
        <template #header>
          <div class="flex items-center gap-2">
            <span class="drag-handle cursor-move text-[var(--n-text-color-3)]" title="drag">⋮⋮</span>
            <span class="truncate font-medium">{{ item.name }}</span>
            <NTag size="tiny" :bordered="false">{{ typeLabel(item.type) }}</NTag>
            <NTag v-if="item.id === store.active_id" size="tiny" type="success">{{ t('page.modelManagement.active') }}</NTag>
            <NTag v-if="!item.enabled" size="tiny" type="warning">{{ t('page.modelManagement.disabled') }}</NTag>
          </div>
        </template>
        <template #header-extra>
          <NSwitch
            size="small"
            :value="item.enabled"
            @update:value="(value: boolean) => toggleProvider(item, value)"
          />
        </template>

        <div class="flex flex-col gap-1 text-xs text-[var(--n-text-color-3)]">
          <div class="truncate">{{ t('page.modelManagement.baseUrl') }}: {{ item.base_url || '-' }}</div>
          <div class="truncate">{{ t('page.modelManagement.defaultModel') }}: {{ item.model || '-' }}</div>
          <div>
            {{ t('page.modelManagement.apiKey') }}:
            <NTag :type="item.api_key_set ? 'success' : 'warning'" size="tiny" :bordered="false">
              {{ item.api_key_set ? item.api_key_masked || t('page.modelManagement.apiKeyConfigured') : t('page.modelManagement.apiKeyMissing') }}
            </NTag>
          </div>
          <div>
            {{ t('page.modelManagement.modelsCount', { count: item.models?.length ?? 0 }) }}
            <template v-if="item.type === 'aggregate'">
              · {{ t('page.modelManagement.upstreamsCount', { count: item.upstreams?.length ?? 0 }) }}
            </template>
          </div>
          <div>
            {{ t('page.modelManagement.lastTest') }}:
            <template v-if="item.last_test?.at">
              <NTag :type="statusTagType(item.last_test.status)" size="tiny" :bordered="false">
                {{ item.last_test.status === 'ok' ? t('page.modelManagement.testOk') : t('page.modelManagement.testFail') }}
              </NTag>
              <span class="ml-1">{{ item.last_test.latency_ms ?? 0 }} ms</span>
            </template>
            <span v-else>{{ t('page.modelManagement.neverTested') }}</span>
          </div>
        </div>

        <div
          v-if="cardTests[item.id]"
          class="mt-2 rounded bg-[var(--n-action-color)] p-2 text-xs break-all text-[var(--n-text-color-3)]"
        >
          {{ cardTests[item.id].detail }}
          <div v-if="cardTests[item.id].reply" class="mt-1 text-[var(--n-text-color-2)]">
            {{ t('page.modelManagement.reply') }}: {{ cardTests[item.id].reply }}
          </div>
        </div>

        <template #action>
          <NSpace :size="6" justify="end">
            <NButton size="tiny" :disabled="item.id === store.active_id" @click="activate(item)">
              {{ t('page.modelManagement.use') }}
            </NButton>
            <NButton size="tiny" :loading="isTesting(item.id)" @click="testProvider(item)">
              {{ t('page.modelManagement.test') }}
            </NButton>
            <NButton size="tiny" @click="openEdit(item)">{{ t('page.modelManagement.edit') }}</NButton>
            <NButton size="tiny" @click="duplicate(item)">{{ t('page.modelManagement.duplicate') }}</NButton>
            <NPopconfirm @positive-click="remove(item)">
              <template #trigger>
                <NButton size="tiny" quaternary type="error">{{ t('page.modelManagement.remove') }}</NButton>
              </template>
              {{ t('page.modelManagement.removeConfirm', { name: item.name }) }}
            </NPopconfirm>
          </NSpace>
        </template>
      </NCard>
    </VueDraggable>

    <NDrawer v-model:show="drawer.show" placement="right" :width="620" resizable :min-width="460" :max-width="900">
      <NDrawerContent
        :title="drawer.mode === 'create' ? t('page.modelManagement.addProvider') : t('page.modelManagement.editProvider')"
        closable
      >
        <NForm label-placement="top" size="small">
          <NFormItem :label="t('page.modelManagement.providerName')">
            <NInput v-model:value="form.name" :placeholder="t('page.modelManagement.providerNamePlaceholder')" />
          </NFormItem>

          <div class="grid grid-cols-1 gap-x-3 md:grid-cols-2">
            <NFormItem :label="t('page.modelManagement.providerType')">
              <NSelect v-model:value="form.type" :options="typeOptions" />
            </NFormItem>
            <NFormItem :label="t('page.modelManagement.protocol')">
              <NSelect v-model:value="form.protocol" :options="protocolOptions" />
            </NFormItem>
          </div>

          <NFormItem v-if="form.type === 'api'" :label="t('page.modelManagement.baseUrl')">
            <NInput v-model:value="form.base_url" placeholder="https://api.openai.com/v1" />
          </NFormItem>

          <NFormItem :label="t('page.modelManagement.apiKey')">
            <NInput
              v-model:value="form.api_key"
              type="password"
              show-password-on="click"
              :placeholder="t('page.modelManagement.apiKeyPlaceholder')"
            />
            <div class="mt-1 text-xs text-[var(--n-text-color-3)]">
              {{ t('page.modelManagement.apiKeyHint') }}
            </div>
          </NFormItem>

          <NFormItem :label="t('page.modelManagement.defaultModel')">
            <div class="flex w-full items-center gap-2">
              <NSelect
                v-model:value="form.model"
                class="flex-1"
                filterable
                tag
                :options="modelOptions"
                :placeholder="t('page.modelManagement.modelPlaceholder')"
              />
              <NButton size="small" :loading="drawer.loadingModels" @click="fetchModels">
                {{ t('page.modelManagement.fetchModels') }}
              </NButton>
            </div>
          </NFormItem>

          <div class="grid grid-cols-1 gap-x-3 md:grid-cols-2">
            <NFormItem :label="t('page.modelManagement.temperature')">
              <NInputNumber v-model:value="form.temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
            </NFormItem>
            <NFormItem :label="t('page.modelManagement.maxTokens')">
              <NInputNumber v-model:value="form.max_tokens" :min="1" :max="65536" style="width: 100%" />
            </NFormItem>
          </div>

          <NFormItem :label="t('page.modelManagement.models')">
            <div class="flex w-full flex-col gap-2">
              <div v-for="(model, index) in form.models" :key="index" class="flex items-center gap-2">
                <NInput v-model:value="model.id" class="flex-1" placeholder="gpt-4o-mini" />
                <NInputNumber
                  v-model:value="model.context_window"
                  class="w-32"
                  :min="0"
                  :placeholder="t('page.modelManagement.contextWindow')"
                />
                <NButton size="small" quaternary type="error" @click="removeModel(index)">×</NButton>
              </div>
              <NButton size="small" dashed @click="addModel">{{ t('page.modelManagement.addModel') }}</NButton>
            </div>
          </NFormItem>

          <NFormItem v-if="form.type === 'aggregate'" :label="t('page.modelManagement.upstreams')">
            <div class="flex w-full flex-col gap-3">
              <div v-for="(upstream, index) in form.upstreams" :key="index" class="rounded border p-2">
                <div class="flex items-center gap-2">
                  <NInput v-model:value="upstream.name" :placeholder="t('page.modelManagement.upstreamName')" />
                  <NSwitch v-model:value="upstream.enabled" size="small" />
                  <NButton size="small" quaternary type="error" @click="removeUpstream(index)">×</NButton>
                </div>
                <NInput v-model:value="upstream.base_url" class="mt-2" placeholder="https://api.example.com/v1" />
                <div class="mt-2 grid grid-cols-1 gap-x-2 md:grid-cols-2">
                  <NSelect v-model:value="upstream.protocol" :options="protocolOptions" />
                  <NInput v-model:value="upstream.model" :placeholder="t('page.modelManagement.defaultModel')" />
                </div>
                <NInput
                  v-model:value="upstream.api_key"
                  class="mt-2"
                  type="password"
                  show-password-on="click"
                  :placeholder="upstream.api_key_set ? upstream.api_key_masked : t('page.modelManagement.apiKeyPlaceholder')"
                />
              </div>
              <NButton size="small" dashed @click="addUpstream">{{ t('page.modelManagement.addUpstream') }}</NButton>
            </div>
          </NFormItem>

          <NFormItem :label="t('page.modelManagement.enabledLabel')">
            <NSwitch v-model:value="form.enabled" />
          </NFormItem>
        </NForm>

        <div v-if="drawer.result" class="rounded bg-[var(--n-action-color)] p-3 text-xs break-all">
          <div class="flex flex-wrap items-center gap-2">
            <NTag :type="statusTagType(drawer.result.status)" size="small">
              {{ drawer.result.status === 'ok' ? t('page.modelManagement.testOk') : t('page.modelManagement.testFail') }}
            </NTag>
            <span class="text-[var(--n-text-color-3)]">{{ drawer.result.latency_ms }} ms</span>
            <span class="text-[var(--n-text-color-3)]">
              {{ t('page.modelManagement.upstreamModels') }}: {{ drawer.result.models_count }}
            </span>
          </div>
          <p class="mt-1">{{ drawer.result.detail }}</p>
          <div v-if="drawer.result.endpoints?.length" class="mt-1 flex flex-col gap-1">
            <div v-for="endpoint in drawer.result.endpoints" :key="endpoint.label">
              {{ endpoint.label }} · {{ endpoint.status === 'ok' ? t('page.modelManagement.testOk') : t('page.modelManagement.testFail') }}
              · {{ endpoint.detail }}
            </div>
          </div>
          <p v-if="drawer.result.reply" class="mt-1">
            <b>{{ t('page.modelManagement.reply') }}:</b> {{ drawer.result.reply }}
          </p>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <NButton size="small" :loading="drawer.testing" @click="testDraft">
              {{ t('page.modelManagement.test') }}
            </NButton>
            <NButton size="small" type="primary" :loading="saving" @click="save">
              {{ t('page.modelManagement.save') }}
            </NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <NModal
      v-model:show="importer.show"
      preset="card"
      class="max-w-[640px]"
      :title="t('page.modelManagement.importTitle')"
    >
      <NInput
        v-model:value="importer.text"
        type="textarea"
        :rows="8"
        :placeholder="t('page.modelManagement.importPlaceholder')"
      />
      <p class="mt-2 text-xs text-[var(--n-text-color-3)]">{{ t('page.modelManagement.importHint') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton size="small" @click="importer.show = false">{{ t('page.modelManagement.cancel') }}</NButton>
          <NButton size="small" type="primary" :loading="importing" @click="submitImport">
            {{ t('page.modelManagement.importConfirm') }}
          </NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>
