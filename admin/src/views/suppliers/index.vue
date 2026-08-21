<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton, NDataTable, NInput, NModal, NForm, NFormItem, NSelect, NSpace, NTag, NEmpty, NDrawer, NDrawerContent,
  useMessage,
} from 'naive-ui';
import { get, post, patch } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const suppliers = ref<any[]>([]);
const activeFilter = ref<string | null>(null);
const showModal = ref(false);
const editing = ref<any>(null);
const { t } = useI18n();
const message = useMessage();
const modalError = ref('');
const modalLoading = ref(false);
const regionsString = ref('');

const filterOptions = [
  { label: t('page.suppliers.active'), value: 'true' },
  { label: t('page.suppliers.inactive'), value: 'false' },
];

const integrationOptions = [
  { label: 'Manual', value: 'manual' },
  { label: 'API', value: 'api' },
  { label: 'Dropship', value: 'dropship' },
];

const providerOptions = ref<{ label: string; value: string }[]>([]);

const form = ref({
  name: '', contact_email: '', contact_phone: '',
  integration_type: 'manual', shipping_regions: [] as string[],
  default_currency: 'USD', provider_code: null as string | null,
});

function updateRegions() {
  form.value.shipping_regions = regionsString.value.split(',').map(s => s.trim()).filter(Boolean);
}

const columns: DataTableColumns<any> = [
  { title: t('page.suppliers.name'), key: 'name' },
  { title: () => t('page.suppliers.contactEmail'), key: 'contact_email', render: row => row.contact_email || '-' },
  { title: t('page.suppliers.integrationType'), key: 'integration_type' },
  { title: t('page.suppliers.provider'), key: 'provider_code', render: row => row.provider_code || '-' },
  { title: t('page.suppliers.shippingRegions'), key: 'shipping_regions', render: row => (row.shipping_regions || []).join(', ') },
  {
    title: t('page.suppliers.active'), key: 'is_active',
    render: row => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? t('page.suppliers.active') : t('page.suppliers.inactive') }),
  },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEdit(row) }, { default: () => t('common.edit') }),
        h(NButton, { size: 'small', type: 'info', disabled: !row.provider_code, onClick: () => openCredentials(row) }, { default: () => t('page.suppliers.credentials') }),
        h(NButton, { size: 'small', type: 'primary', disabled: !row.provider_code, onClick: () => openSearch(row) }, { default: () => t('page.suppliers.searchProducts') }),
        h(NButton, { size: 'small', type: 'warning', disabled: !row.provider_code, loading: row._syncing, onClick: () => runSync(row) }, { default: () => t('page.suppliers.syncNow') }),
        h(NButton, { size: 'small', disabled: !row.provider_code, onClick: () => openLogs(row) }, { default: () => t('page.suppliers.syncLogs') }),
        row.is_active ? h(NButton, { size: 'small', type: 'warning', onClick: () => deactivate(row.id) }, { default: () => t('page.suppliers.inactive') }) : null,
      ],
    }),
  },
];

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = {};
    if (activeFilter.value !== null) params.is_active = activeFilter.value === 'true';
    const res = await get('/api/admin/v1/suppliers/', { params });
    suppliers.value = res.data?.items || res.data || [];
  } finally {
    loading.value = false;
  }
}

async function loadProviders() {
  try {
    const res = await get('/api/admin/v1/supplier-sources/providers');
    const list = res.data?.data || [];
    providerOptions.value = list.map((p: any) => ({ label: p.display_name || p.provider_code, value: p.provider_code }));
  } catch {
    providerOptions.value = [];
  }
}

function openCreate() {
  editing.value = null;
  form.value = { name: '', contact_email: '', contact_phone: '', integration_type: 'manual', shipping_regions: [], default_currency: 'USD', provider_code: null };
  regionsString.value = '';
  modalError.value = '';
  showModal.value = true;
}

function openEdit(s: any) {
  editing.value = s;
  form.value = {
    name: s.name, contact_email: s.contact_email || '', contact_phone: s.contact_phone || '',
    integration_type: s.integration_type || 'manual', shipping_regions: s.shipping_regions || [],
    default_currency: s.default_currency || 'USD', provider_code: s.provider_code || null,
  };
  regionsString.value = (s.shipping_regions || []).join(', ');
  modalError.value = '';
  showModal.value = true;
}

async function save() {
  modalLoading.value = true;
  modalError.value = '';
  try {
    const payload: any = { ...form.value };
    if (editing.value) {
      await patch(`/api/admin/v1/suppliers/${editing.value.id}`, payload);
    } else {
      await post('/api/admin/v1/suppliers/', payload);
    }
    showModal.value = false;
    fetch();
  } catch (e: any) {
    modalError.value = e.response?.data?.detail || 'Save failed';
  } finally {
    modalLoading.value = false;
  }
}

async function deactivate(id: string) {
  try { await post(`/api/admin/v1/suppliers/${id}/deactivate`); fetch(); } catch (e) { console.error(e); }
}

// ---- 凭据 ----
const showCredModal = ref(false);
const credLoading = ref(false);
const credError = ref('');
const credForm = ref({ access_token: '', token_type: 'Bearer' });
let credSupplierId = '';

function openCredentials(row: any) {
  credSupplierId = row.id;
  credForm.value = { access_token: '', token_type: 'Bearer' };
  credError.value = '';
  showCredModal.value = true;
  get(`/api/admin/v1/supplier-sources/${row.id}/credentials`)
    .then(res => {
      const d = res.data?.data;
      if (d && d.access_token) credForm.value = { access_token: d.access_token, token_type: d.token_type || 'Bearer' };
    })
    .catch(() => {});
}

async function saveCredentials() {
  credLoading.value = true;
  credError.value = '';
  try {
    await patch(`/api/admin/v1/supplier-sources/${credSupplierId}/credentials`, credForm.value);
    message.success(t('page.suppliers.credSaved'));
    showCredModal.value = false;
  } catch (e: any) {
    credError.value = e.response?.data?.detail || 'Save failed';
  } finally {
    credLoading.value = false;
  }
}

// ---- 货源搜索 / 导入 ----
const showSearchModal = ref(false);
const searchLoading = ref(false);
const importLoading = ref(false);
const searchKeyword = ref('');
const searchItems = ref<any[]>([]);
const checkedIds = ref<string[]>([]);
let searchSupplierId = '';

function openSearch(row: any) {
  searchSupplierId = row.id;
  searchKeyword.value = '';
  searchItems.value = [];
  checkedIds.value = [];
  showSearchModal.value = true;
}

async function doSearch() {
  searchLoading.value = true;
  try {
    const res = await get(`/api/admin/v1/supplier-sources/${searchSupplierId}/search`, {
      params: { keyword: searchKeyword.value, page: 1, page_size: 20 },
    });
    const data = res.data?.data || {};
    searchItems.value = data.items || [];
    checkedIds.value = [];
  } catch (e: any) {
    message.error(e.response?.data?.detail || 'Search failed');
  } finally {
    searchLoading.value = false;
  }
}

const searchColumns: DataTableColumns<any> = [
  { type: 'selection' },
  { title: t('page.suppliers.name'), key: 'title' },
  { title: t('page.suppliers.price'), key: 'price', render: row => `${row.currency || ''} ${row.price}` },
  { title: t('page.suppliers.inventory'), key: 'inventory' },
  { title: 'SKU', key: 'sku' },
];

async function doImport() {
  if (!checkedIds.value.length) return;
  importLoading.value = true;
  try {
    const res = await post(`/api/admin/v1/supplier-sources/${searchSupplierId}/import`, {
      provider_product_ids: checkedIds.value,
    });
    const d = res.data?.data || {};
    const imported = (d.imported || []).length;
    const failed = (d.failed || []).length;
    message.success(t('page.suppliers.importResult', { imported, failed }));
    showSearchModal.value = false;
  } catch (e: any) {
    message.error(e.response?.data?.detail || 'Import failed');
  } finally {
    importLoading.value = false;
  }
}

// ---- 同步 ----
async function runSync(row: any) {
  row._syncing = true;
  try {
    const res = await post(`/api/admin/v1/supplier-sources/${row.id}/sync`, { trigger_type: 'manual' });
    const d = res.data?.data || {};
    if (d.status === 'failed') message.warning(t('page.suppliers.syncFailed'));
    else message.success(t('page.suppliers.syncDone'));
  } catch (e: any) {
    message.error(e.response?.data?.detail || 'Sync failed');
  } finally {
    row._syncing = false;
  }
}

// ---- 同步日志 ----
const showLogsDrawer = ref(false);
const syncLogs = ref<any[]>([]);

function openLogs(row: any) {
  syncLogs.value = [];
  showLogsDrawer.value = true;
  get(`/api/admin/v1/supplier-sources/${row.id}/sync-logs`, { params: { limit: 20 } })
    .then(res => { syncLogs.value = res.data?.data || []; })
    .catch(() => {});
}

const logColumns: DataTableColumns<any> = [
  { title: t('page.suppliers.triggerType'), key: 'trigger_type', render: row => row.trigger_type === 'scheduled' ? t('page.suppliers.scheduled') : t('page.suppliers.manual') },
  {
    title: t('page.suppliers.syncStatus'), key: 'status',
    render: row => {
      const map: Record<string, any> = { success: 'success', running: 'warning', partial: 'warning', failed: 'error' };
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status });
    },
  },
  { title: t('page.suppliers.itemsTotal'), key: 'items_total' },
  { title: t('page.suppliers.itemsImported'), key: 'items_imported' },
  { title: t('page.suppliers.itemsUpdated'), key: 'items_updated' },
  { title: t('page.suppliers.startedAt'), key: 'started_at', render: row => (row.started_at || '').replace('T', ' ') },
];

onMounted(() => { loadProviders(); fetch(); });
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <NSpace>
        <NSelect
          v-model:value="activeFilter"
          :options="filterOptions"
          :placeholder="$t('page.suppliers.status')"
          clearable
          style="width:140px"
          @update:value="fetch"
        />
      </NSpace>
      <NButton type="primary" @click="openCreate">{{ $t('page.suppliers.addSupplier') }}</NButton>
    </div>

    <NDataTable
      :columns="columns"
      :data="suppliers"
      :loading="loading"
      :bordered="false"
      size="small"
    />

    <!-- 创建 / 编辑供应商 -->
    <NModal
      v-model:show="showModal"
      preset="card"
      :title="editing ? $t('page.suppliers.editSupplier') : $t('page.suppliers.addSupplier')"
      style="width:520px"
    >
      <NForm :model="form" label-placement="left" label-width="140">
        <NFormItem :label="$t('page.suppliers.name')" required><NInput v-model:value="form.name" /></NFormItem>
        <NFormItem :label="$t('page.suppliers.contactEmail')"><NInput v-model:value="form.contact_email" type="text" /></NFormItem>
        <NFormItem :label="$t('page.suppliers.contactPhone')"><NInput v-model:value="form.contact_phone" /></NFormItem>
        <NFormItem :label="$t('page.suppliers.integrationType')">
          <NSelect v-model:value="form.integration_type" :options="integrationOptions" />
        </NFormItem>
        <NFormItem :label="$t('page.suppliers.providerCode')">
          <NSelect
            v-model:value="form.provider_code"
            :options="providerOptions"
            :placeholder="$t('page.suppliers.providerCodePlaceholder')"
            :disabled="!!editing"
            clearable
            filterable
          />
        </NFormItem>
        <NFormItem :label="$t('page.suppliers.shippingRegions')">
          <NInput v-model:value="regionsString" placeholder="comma separated" @update:value="updateRegions" />
        </NFormItem>
        <NFormItem :label="$t('page.suppliers.defaultCurrency')"><NInput v-model:value="form.default_currency" /></NFormItem>
      </NForm>
      <div v-if="modalError" class="text-red-500 text-sm mt-2">{{ modalError }}</div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showModal = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="modalLoading" @click="save">{{ $t('common.save') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 凭据配置 -->
    <NModal v-model:show="showCredModal" preset="card" :title="$t('page.suppliers.credentials')" style="width:520px">
      <NForm label-placement="left" label-width="140">
        <NFormItem :label="$t('page.suppliers.accessToken')" required>
          <NInput v-model:value="credForm.access_token" type="textarea" :rows="3" />
        </NFormItem>
        <NFormItem :label="$t('page.suppliers.tokenType')">
          <NInput v-model:value="credForm.token_type" placeholder="Bearer" />
        </NFormItem>
      </NForm>
      <div v-if="credError" class="text-red-500 text-sm mt-2">{{ credError }}</div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCredModal = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="credLoading" @click="saveCredentials">{{ $t('page.suppliers.saveCredentials') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 货源搜索 / 导入 -->
    <NModal v-model:show="showSearchModal" preset="card" :title="$t('page.suppliers.searchProducts')" style="width:860px">
      <NSpace class="mb-3">
        <NInput
          v-model:value="searchKeyword"
          :placeholder="$t('page.suppliers.searchPlaceholder')"
          style="width:320px"
          @keyup.enter="doSearch"
        />
        <NButton type="primary" :loading="searchLoading" @click="doSearch">{{ $t('page.suppliers.search') }}</NButton>
        <NButton
          type="primary"
          :disabled="!checkedIds.length"
          :loading="importLoading"
          @click="doImport"
        >
          {{ $t('page.suppliers.importSelected') }} ({{ checkedIds.length }})
        </NButton>
      </NSpace>
      <NDataTable
        v-if="searchItems.length"
        :columns="searchColumns"
        :data="searchItems"
        :row-key="(row: any) => row.provider_product_id"
        :checked-row-keys="checkedIds"
        :bordered="false"
        size="small"
        @update:checked-row-keys="(keys: any[]) => (checkedIds = keys)"
      />
      <NEmpty v-else :description="$t('page.suppliers.noSearchResult')" />
    </NModal>

    <!-- 同步日志 -->
    <NDrawer v-model:show="showLogsDrawer" placement="right" :width="680">
      <NDrawerContent :title="$t('page.suppliers.syncLogs')">
        <NDataTable
          v-if="syncLogs.length"
          :columns="logColumns"
          :data="syncLogs"
          :bordered="false"
          size="small"
        />
        <NEmpty v-else :description="$t('page.suppliers.noLogs')" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
