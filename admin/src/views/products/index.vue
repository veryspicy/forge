<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <NSpace>
        <NInput v-model:value="search" :placeholder="$t('common.search')" style="width:200px" @keyup.enter="loadProducts" />
        <NButton @click="loadProducts">{{ $t('common.search') }}</NButton>
        <NSelect v-model:value="category" :options="categoryOptions" :placeholder="$t('page.products.allCategories')" clearable @update:value="loadProducts" />
      </NSpace>
      <NSpace>
        <NButton @click="onExport">{{ $t('page.products.export') }}</NButton>
        <NButton @click="triggerImport">{{ $t('page.products.import') }}</NButton>
        <input ref="fileInput" type="file" accept=".csv" class="hidden" @change="onImportFile" />
        <NButton type="primary" @click="$router.push('/products/new')">{{ $t('common.add') }}</NButton>
      </NSpace>
    </div>

    <NDataTable :columns="columns" :data="products" :loading="loading" :bordered="false" size="small" />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>

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

<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { NButton, NDataTable, NImage, NInput, NModal, NPagination, NSelect, NSpace, NTag } from 'naive-ui';
import { get, post } from '@/service/api/helper';
import { localStg } from '@/utils/storage';
import type { DataTableColumns } from 'naive-ui';

const router = useRouter();
const { t } = useI18n();
const loading = ref(false);
const search = ref('');
const category = ref<string | null>(null);
const products = ref<any[]>([]);
const page = ref(1);
const total = ref(0);
const pageSize = 20;
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

const columns: DataTableColumns<any> = [
  {
    title: t('common.image'), key: 'image', width: 60,
    render: row => row.images?.[0]?.url
      ? h(NImage, { src: row.images[0].url, width: 40, height: 40, style: { objectFit: 'cover', borderRadius: '4px' } })
      : h('span', { style: { color: 'var(--n-text-color-3)' } }, '--'),
  },
  { title: t('common.sku'), key: 'sku', render: row => row.sku || '-' },
  { title: t('common.name'), key: 'name' },
  { title: t('page.products.category'), key: 'category' },
  { title: t('page.products.price'), key: 'price', render: row => `$${row.price}` },
  { title: t('common.inventory'), key: 'inventory' },
  {
    title: t('page.productsDetail.aiGenerated'), key: 'is_ai_generated',
    render: row => h(NTag, { type: row.is_ai_generated ? 'info' : 'default', size: 'small' }, { default: () => row.is_ai_generated ? t('common.yes') : t('common.no') }),
  },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NButton, { size: 'small', onClick: () => router.push(`/products/${row.id}`) }, { default: () => t('common.edit') }),
  },
];

async function loadProducts() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (search.value) params.search = search.value;
    if (category.value) params.category = category.value;
    const res = await get('/api/admin/v1/products/', params);
    const body = (res as any)?.data ?? res;
    products.value = body?.items ?? [];
    total.value = body?.total ?? 0;
  } finally { loading.value = false; }
}

function goPage(p: number) { page.value = p; loadProducts(); }

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
    window.$message?.error(String(err));
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
    window.$message?.error(String(err));
  }
}

onMounted(loadProducts);
</script>
