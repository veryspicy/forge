<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import {
  NButton, NCard, NDataTable, NImage, NInput, NModal, NPagination, NPopconfirm, NSelect,
  NSpace, NSwitch, NTag, useMessage
} from 'naive-ui';
import { get, post, del } from '@/service/api/helper';
import { localStg } from '@/utils/storage';
import type { DataTableColumns } from 'naive-ui';

const router = useRouter();
const { t } = useI18n();
const message = useMessage();
const loading = ref(false);
const search = ref('');
const category = ref<string | null>(null);
const status = ref<string | null>(null);
const products = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const checkedRowKeys = ref<Array<string | number>>([]);
const fileInput = ref<HTMLInputElement | null>(null);
const showImportModal = ref(false);
const importResult = ref<{ created: number; updated: number; failed: number; errors: Array<{ row: number; sku: string; error: string }> } | null>(null);

const errorColumns: DataTableColumns<any> = [
  { title: t('page.products.importRow'), key: 'row', width: 70 },
  { title: t('common.sku'), key: 'sku', width: 140 },
  { title: t('page.products.importError'), key: 'error' },
];

const categoryOptions = [
  { label: 'Food', value: 'FOOD' },
  { label: 'Toy', value: 'TOY' },
  { label: 'Health', value: 'HEALTH' },
  { label: 'Accessory', value: 'ACCESSORY' },
  { label: 'Service', value: 'SERVICE' },
];

const statusOptions = [
  { label: t('page.products.draft'), value: 'draft' },
  { label: t('page.products.active'), value: 'active' },
  { label: t('page.products.inactive'), value: 'inactive' },
  { label: t('page.products.deleted'), value: 'deleted' },
];

function statusTagType(value: string): 'default' | 'success' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
    draft: 'default',
    active: 'success',
    inactive: 'warning',
    deleted: 'error',
  };
  return map[value] ?? 'default';
}

function statusLabel(row: any): string {
  const key = row.status as string;
  const labels: Record<string, string> = {
    draft: t('page.products.draft'),
    active: t('page.products.active'),
    inactive: t('page.products.inactive'),
    deleted: t('page.products.deleted'),
  };
  return labels[key] ?? key;
}

async function toggleStatus(row: any) {
  const next = row.status === 'active' ? 'inactive' : 'active';
  try {
    await post(`/api/admin/v1/products/${row.id}/status`, { status: next });
    row.status = next;
    message.success(t('page.products.statusUpdated'));
  } catch (err) {
    message.error(String(err));
  }
}

async function deleteProduct(row: any) {
  try {
    await del(`/api/admin/v1/products/${row.id}`);
    message.success(t('page.products.deleteSuccess'));
    loadProducts();
  } catch (err) {
    message.error(String(err));
  }
}

const columns: DataTableColumns<any> = [
  { type: 'selection', width: 40 },
  {
    title: t('common.image'), key: 'image', width: 70,
    render: row => row.images?.[0]?.url
      ? h(NImage, { src: row.images[0].url, width: 44, height: 44, style: { objectFit: 'cover', borderRadius: '4px' } })
      : h('span', { style: { color: 'var(--n-text-color-3)' } }, '--'),
  },
  { title: t('common.sku'), key: 'sku', render: row => row.sku || '-' },
  { title: t('common.name'), key: 'name', ellipsis: { tooltip: true } },
  { title: t('page.products.category'), key: 'category', width: 120, render: row => row.category || '-' },
  { title: t('page.products.price'), key: 'price', width: 100, render: row => `$${Number(row.price ?? 0).toFixed(2)}` },
  { title: t('common.inventory'), key: 'inventory', width: 90, render: row => row.inventory ?? 0 },
  {
    title: t('page.products.status'), key: 'status', width: 110,
    render: row => h(NTag, { type: statusTagType(row.status), size: 'small', bordered: false }, { default: () => statusLabel(row) }),
  },
  {
    title: t('page.suppliers.actions'), key: 'actions', width: 170,
    render: row => h(NSpace, { size: 8, align: 'center' }, {
      default: () => [
        h(NSwitch, {
          size: 'small',
          value: row.status === 'active',
          disabled: row.status === 'deleted' || row.status === 'draft',
          'on-update:value': () => toggleStatus(row),
        }),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => router.push(`/products/${row.id}`) }, { default: () => t('common.edit') }),
        h(NPopconfirm, {
          onPositiveClick: () => deleteProduct(row),
        }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => t('common.delete') }),
          default: () => t('page.products.deleteConfirm'),
        }),
      ],
    }),
  },
];

async function loadProducts() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value };
    if (search.value) params.search = search.value;
    if (category.value) params.category = category.value;
    if (status.value) params.status = status.value;
    const res = await get('/api/admin/v1/products/', params);
    const body = (res as any)?.data ?? res;
    products.value = body?.items ?? [];
    total.value = body?.total ?? 0;
  } finally {
    loading.value = false;
  }
}

function handleQuery() {
  page.value = 1;
  loadProducts();
}

function handleReset() {
  search.value = '';
  category.value = null;
  status.value = null;
  page.value = 1;
  loadProducts();
}

function goPage(p: number) { page.value = p; loadProducts(); }

async function batchStatus(target: string) {
  if (!checkedRowKeys.value.length) {
    message.warning(t('page.products.selectProduct'));
    return;
  }
  try {
    const res = await post('/api/admin/v1/products/batch-status', {
      ids: checkedRowKeys.value,
      status: target,
    });
    const data = (res as any)?.data ?? res;
    message.success(`${t('page.products.statusUpdated')}（${data?.updated ?? 0}）`);
    checkedRowKeys.value = [];
    loadProducts();
  } catch (err) {
    message.error(String(err));
  }
}

async function batchDelete() {
  if (!checkedRowKeys.value.length) {
    message.warning(t('page.products.selectProduct'));
    return;
  }
  try {
    await post('/api/admin/v1/products/batch-status', { ids: checkedRowKeys.value, status: 'deleted' });
    message.success(t('page.products.deleteSuccess'));
    checkedRowKeys.value = [];
    loadProducts();
  } catch (err) {
    message.error(String(err));
  }
}

async function onExport() {
  const token = localStg.get('token');
  try {
    const res = await fetch('/api/admin/v1/products/export', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `products_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    message.error(String(err));
  }
}

function triggerImport() {
  fileInput.value?.click();
}

async function onImportFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await post('/api/admin/v1/products/import', formData, { 'Content-Type': 'multipart/form-data' });
    importResult.value = res.data;
    showImportModal.value = true;
    loadProducts();
  } catch (err) {
    message.error(String(err));
  }
}

onMounted(loadProducts);
</script>

<template>
  <div class="flex flex-col gap-4">
    <NCard :bordered="false" size="small">
      <NSpace align="center" wrap>
        <NInput v-model:value="search" :placeholder="$t('page.products.searchPlaceholder')" clearable style="width: 260px" @keyup.enter="handleQuery" />
        <NSelect v-model:value="category" :options="categoryOptions" :placeholder="$t('page.products.allCategories')" clearable style="width: 160px" />
        <NSelect v-model:value="status" :options="statusOptions" :placeholder="$t('page.products.allStatus')" clearable style="width: 140px" />
        <NButton type="primary" @click="handleQuery">{{ $t('page.products.query') }}</NButton>
        <NButton @click="handleReset">{{ $t('page.products.reset') }}</NButton>
      </NSpace>
    </NCard>

    <NCard :bordered="false" size="small">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="text-base font-medium">{{ $t('page.products.productList') }}</span>
          <NSpace>
            <NButton size="small" @click="onExport">{{ $t('page.products.export') }}</NButton>
            <NButton size="small" @click="triggerImport">{{ $t('page.products.import') }}</NButton>
            <input ref="fileInput" type="file" accept=".csv" class="hidden" @change="onImportFile" />
            <NButton size="small" type="primary" @click="$router.push('/products/new')">{{ $t('common.add') }}</NButton>
          </NSpace>
        </div>
      </template>

      <NSpace class="mb-3" align="center">
        <span class="text-sm">{{ $t('page.products.batchActions') }}:</span>
        <NButton size="small" type="success" secondary :disabled="!checkedRowKeys.length" @click="batchStatus('active')">{{ $t('page.products.batchEnable') }}</NButton>
        <NButton size="small" type="warning" secondary :disabled="!checkedRowKeys.length" @click="batchStatus('inactive')">{{ $t('page.products.batchDisable') }}</NButton>
        <NButton size="small" type="error" secondary :disabled="!checkedRowKeys.length" @click="batchDelete">{{ $t('page.products.batchDelete') }}</NButton>
      </NSpace>

      <NDataTable
        :columns="columns"
        :data="products"
        :loading="loading"
        :bordered="false"
        size="small"
        :row-key="row => row.id"
        :checked-row-keys="checkedRowKeys"
        @update:checked-row-keys="checkedRowKeys = $event"
      />

      <div class="flex justify-between items-center mt-4">
        <span class="text-sm text-gray-500">{{ $t('page.products.total', { n: total }) }}</span>
        <NSpace align="center">
          <span class="text-sm text-gray-500">{{ $t('page.products.perPage') }}</span>
          <NSelect
            v-model:value="pageSize"
            :options="[{ label: '10', value: 10 }, { label: '20', value: 20 }, { label: '50', value: 50 }]"
            style="width: 80px"
            @update:value="page = 1; loadProducts()"
          />
          <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
        </NSpace>
      </div>
    </NCard>

    <NModal v-model:show="showImportModal" preset="card" :title="$t('page.products.importResult')" style="width: 720px">
      <NSpace vertical>
        <NSpace>
          <NTag type="success" :bordered="false">{{ $t('page.products.importCreated') }}: {{ importResult?.created ?? 0 }}</NTag>
          <NTag type="info" :bordered="false">{{ $t('page.products.importUpdated') }}: {{ importResult?.updated ?? 0 }}</NTag>
          <NTag :type="(importResult?.failed ?? 0) > 0 ? 'error' : 'default'" :bordered="false">{{ $t('page.products.importFailed') }}: {{ importResult?.failed ?? 0 }}</NTag>
        </NSpace>
        <NDataTable v-if="importResult?.errors?.length" :columns="errorColumns" :data="importResult.errors" size="small" :bordered="false" />
      </NSpace>
    </NModal>
  </div>
</template>
