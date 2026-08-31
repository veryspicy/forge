<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NImage,
  NInput,
  NInputNumber,
  NModal,
  NPagination,
  NPopconfirm,
  NSelect,
  NSpace,
  NSwitch,
  NTag,
  useMessage
} from 'naive-ui';
import { get, post, patch, del } from '@/service/api/helper';
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
const importResult = ref<{
  created: number;
  updated: number;
  failed: number;
  errors: Array<{ row: number; sku: string; error: string }>;
} | null>(null);

// SKU 抽屉状态
const showSkuDrawer = ref(false);
const skuProduct = ref<any>(null);
const variants = ref<any[]>([]);
const variantLoading = ref(false);
const variantSaving = ref(false);
const editingIndex = ref(-1); // -1 表示无编辑行；>=0 表示正在编辑的行
const addingVariant = ref(false); // 是否处于"新增 SKU"模式
const variantForm = ref({
  id: '',
  name: '',
  sku: '',
  price: null as number | null,
  cost: null as number | null,
  inventory: 0,
  status: 'active',
  is_default: false,
  specRows: [] as { key: string; value: string }[]
});

const variantStatusOptions = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'inactive' }
];

function addSpecRow() {
  variantForm.value.specRows.push({ key: '', value: '' });
}

function removeSpecRow(idx: number) {
  variantForm.value.specRows.splice(idx, 1);
}

function resetVariantForm() {
  variantForm.value = {
    id: '',
    name: '',
    sku: '',
    price: null,
    cost: null,
    inventory: 0,
    status: 'active',
    is_default: false,
    specRows: []
  };
}

function attrsToSpecRows(attrs: Record<string, any> | null | undefined): { key: string; value: string }[] {
  const rows: { key: string; value: string }[] = [];
  for (const [k, v] of Object.entries(attrs ?? {})) {
    rows.push({ key: String(k), value: v == null ? '' : String(v) });
  }
  return rows;
}

async function openSkuDrawer(row: any) {
  skuProduct.value = row;
  showSkuDrawer.value = true;
  resetVariantForm();
  editingIndex.value = -1;
  await loadVariants();
}

function startEditVariant(row: any, index: number) {
  addingVariant.value = false;
  editingIndex.value = index;
  variantForm.value = {
    id: row.id,
    name: row.name ?? '',
    sku: row.sku ?? '',
    price: row.price ?? null,
    cost: row.cost ?? null,
    inventory: row.inventory ?? 0,
    status: row.status ?? 'active',
    is_default: Boolean(row.is_default),
    specRows: attrsToSpecRows(
      row.attributes ??
        (row.specs ? Object.fromEntries((row.specs as any[]).map((s: any) => [s.spec_key, s.value])) : null)
    )
  };
}

function cancelEditVariant() {
  editingIndex.value = -1;
  addingVariant.value = false;
  resetVariantForm();
}

function startAddVariant() {
  editingIndex.value = -1;
  addingVariant.value = true;
  resetVariantForm();
}

async function loadVariants() {
  if (!skuProduct.value) return;
  variantLoading.value = true;
  try {
    const res = await get(`/api/admin/v1/products/${skuProduct.value.id}/variants`);
    variants.value = res.data?.data ?? res.data ?? [];
    skuProduct.value.variant_count = variants.value.length;
  } finally {
    variantLoading.value = false;
  }
}

function buildAttributes(): Record<string, any> | null {
  const attrs: Record<string, any> = {};
  for (const row of variantForm.value.specRows) {
    const key = (row.key ?? '').trim();
    if (!key) continue;
    if (key in attrs) {
      message.error(`规格名重复: ${key}`);
      return null;
    }
    attrs[key] = (row.value ?? '').trim();
  }
  return attrs;
}

async function saveVariant() {
  const attributes = buildAttributes();
  if (!attributes) return;

  const payload: Record<string, any> = {
    name: variantForm.value.name,
    sku: variantForm.value.sku.trim(),
    attributes,
    price: variantForm.value.price,
    cost: variantForm.value.cost,
    inventory: variantForm.value.inventory ?? 0,
    status: variantForm.value.status,
    is_default: variantForm.value.is_default
  };

  variantSaving.value = true;
  try {
    if (variantForm.value.id) {
      await patch(`/api/admin/v1/products/${skuProduct.value.id}/variants/${variantForm.value.id}`, payload);
    } else {
      await post(`/api/admin/v1/products/${skuProduct.value.id}/variants`, payload);
    }
    message.success('SKU 已保存');
    cancelEditVariant();
    await loadVariants();
    loadProducts();
  } catch (err) {
    message.error(String(err));
  } finally {
    variantSaving.value = false;
  }
}

async function deleteVariant(row: any) {
  try {
    await del(`/api/admin/v1/products/${skuProduct.value.id}/variants/${row.id}`);
    message.success('SKU 已删除');
    cancelEditVariant();
    await loadVariants();
    loadProducts();
  } catch (err) {
    message.error(String(err));
  }
}

const variantColumns: DataTableColumns<any> = [
  { title: '名称', key: 'name', render: row => row.name || '-' },
  { title: 'SKU', key: 'sku', width: 140, render: row => row.sku || '-' },
  {
    title: '价格',
    key: 'price',
    width: 80,
    render: row => (row.price != null ? `$${Number(row.price).toFixed(2)}` : '-')
  },
  { title: '库存', key: 'inventory', width: 70, render: row => row.inventory ?? 0 },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: row =>
      h(
        NTag,
        { size: 'small', bordered: false, type: row.status === 'active' ? 'success' : 'default' },
        { default: () => (row.status === 'active' ? '启用' : '停用') }
      )
  },
  {
    title: '默认',
    key: 'is_default',
    width: 60,
    render: row =>
      row.is_default ? h(NTag, { size: 'small', bordered: false, type: 'warning' }, { default: () => '默认' }) : '-'
  },
  {
    title: '操作',
    key: 'actions',
    width: 130,
    render: (row, index) =>
      h(
        NSpace,
        { size: 4 },
        {
          default: () => [
            h(
              NButton,
              { size: 'tiny', quaternary: true, type: 'primary', onClick: () => startEditVariant(row, index) },
              { default: () => '编辑' }
            ),
            h(
              NPopconfirm,
              {
                onPositiveClick: () => deleteVariant(row)
              },
              {
                trigger: () => h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, { default: () => '删除' }),
                default: () => '确认删除该 SKU？'
              }
            )
          ]
        }
      )
  }
];

const errorColumns: DataTableColumns<any> = [
  { title: t('page.products.importRow'), key: 'row', width: 70 },
  { title: t('common.sku'), key: 'sku', width: 140 },
  { title: t('page.products.importError'), key: 'error' }
];

const categoryOptions = [
  { label: 'Food', value: 'FOOD' },
  { label: 'Toy', value: 'TOY' },
  { label: 'Health', value: 'HEALTH' },
  { label: 'Accessory', value: 'ACCESSORY' },
  { label: 'Service', value: 'SERVICE' }
];

const statusOptions = [
  { label: t('page.products.draft'), value: 'draft' },
  { label: t('page.products.active'), value: 'active' },
  { label: t('page.products.inactive'), value: 'inactive' },
  { label: t('page.products.deleted'), value: 'deleted' }
];

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

function auditLabel(row: any): string {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '未通过'
  };
  return map[row.audit_status] ?? row.audit_status ?? '--';
}

function auditTagType(value: string): 'default' | 'success' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'error'
  };
  return map[value] ?? 'default';
}

async function toggleFlag(row: any, field: 'is_new' | 'is_recommend') {
  try {
    await patch(`/api/admin/v1/products/${row.id}`, { [field]: !row[field] });
    row[field] = !row[field];
    message.success(t('page.products.statusUpdated'));
  } catch (err) {
    message.error(String(err));
  }
}

async function updateSortOrder(row: any, value: number | null) {
  const next = value ?? 0;
  if (next === row.sort_order) return;
  try {
    await patch(`/api/admin/v1/products/${row.id}`, { sort_order: next });
    row.sort_order = next;
    message.success(t('page.products.statusUpdated'));
  } catch (err) {
    message.error(String(err));
    loadProducts();
  }
}

const columns: DataTableColumns<any> = [
  { type: 'selection', width: 40 },
  { title: '编号', key: 'id', width: 80, render: row => h('span', { style: 'color: var(--n-text-color-3)' }, row.id) },
  {
    title: t('common.image'),
    key: 'image',
    width: 70,
    render: row =>
      row.images?.[0]?.url
        ? h(NImage, {
            src: row.images[0].url,
            width: 44,
            height: 44,
            style: { objectFit: 'cover', borderRadius: '4px' }
          })
        : h('span', { style: { color: 'var(--n-text-color-3)' } }, '--')
  },
  {
    title: t('common.name'),
    key: 'name',
    ellipsis: { tooltip: true },
    render: row =>
      h('div', { style: 'display:flex;flex-direction:column;gap:2px' }, [
        h('span', { style: 'font-weight:500' }, row.name || '-'),
        h('span', { style: 'color:var(--n-text-color-3);font-size:12px' }, `品牌: ${row.brand || '--'}`)
      ])
  },
  {
    title: t('page.products.price'),
    key: 'price',
    width: 140,
    render: row =>
      h('div', { style: 'display:flex;flex-direction:column;gap:2px' }, [
        h('span', { style: 'font-weight:500' }, `$${Number(row.price ?? 0).toFixed(2)}`),
        h('span', { style: 'color:var(--n-text-color-3);font-size:12px' }, `货号: ${row.sku || '--'}`)
      ])
  },
  {
    title: '标签',
    key: 'tags',
    width: 190,
    render: row =>
      h(
        NSpace,
        { size: 8, align: 'center' },
        {
          default: () => [
            h('div', { style: 'display:flex;flex-direction:column;align-items:center;gap:2px' }, [
              h(NSwitch, {
                size: 'small',
                value: row.status === 'active',
                disabled: row.status === 'deleted' || row.status === 'draft',
                'on-update:value': () => toggleStatus(row)
              }),
              h('span', { style: 'color:var(--n-text-color-3);font-size:12px' }, '上架')
            ]),
            h('div', { style: 'display:flex;flex-direction:column;align-items:center;gap:2px' }, [
              h(NSwitch, {
                size: 'small',
                value: Boolean(row.is_new),
                'on-update:value': () => toggleFlag(row, 'is_new')
              }),
              h('span', { style: 'color:var(--n-text-color-3);font-size:12px' }, '新品')
            ]),
            h('div', { style: 'display:flex;flex-direction:column;align-items:center;gap:2px' }, [
              h(NSwitch, {
                size: 'small',
                value: Boolean(row.is_recommend),
                'on-update:value': () => toggleFlag(row, 'is_recommend')
              }),
              h('span', { style: 'color:var(--n-text-color-3);font-size:12px' }, '推荐')
            ])
          ]
        }
      )
  },
  {
    title: '排序',
    key: 'sort_order',
    width: 120,
    align: 'center',
    render: row =>
      h(NInputNumber, {
        size: 'small',
        value: row.sort_order ?? 0,
        min: 0,
        style: 'width: 96px',
        'on-update:value': (val: number | null) => updateSortOrder(row, val)
      })
  },
  {
    title: 'SKU库存',
    key: 'skuInventory',
    width: 110,
    render: row =>
      h(
        'div',
        {
          style:
            'display:inline-flex;align-items:center;justify-content:center;min-width:30px;height:30px;border-radius:50%;background:#1677ff;color:#fff;font-weight:600;font-size:13px;padding:0 8px;cursor:pointer;user-select:none',
          title: `${row.variant_count ?? 0} 个 SKU，点击查看明细`,
          onClick: () => openSkuDrawer(row)
        },
        `${row.total_inventory ?? 0}`
      )
  },
  { title: '销量', key: 'sales', width: 80, render: row => row.sales ?? 0 },
  {
    title: '审核状态',
    key: 'audit_status',
    width: 110,
    render: row =>
      h(
        NSpace,
        { size: 4, align: 'center' },
        {
          default: () => [
            h(
              NTag,
              { size: 'small', bordered: false, type: auditTagType(row.audit_status) },
              { default: () => auditLabel(row) }
            ),
            h(
              'a',
              {
                style: 'color:#1677ff;font-size:12px;cursor:pointer',
                onClick: () => router.push(`/products/${row.id}`)
              },
              '审核详情'
            )
          ]
        }
      )
  },
  {
    title: t('page.suppliers.actions'),
    key: 'actions',
    width: 190,
    render: row =>
      h(
        NSpace,
        { size: 8, align: 'center' },
        {
          default: () => [
            h(
              NButton,
              { size: 'small', quaternary: true, type: 'primary', onClick: () => router.push(`/products/${row.id}`) },
              { default: () => '查看' }
            ),
            h(
              NButton,
              { size: 'small', quaternary: true, type: 'primary', onClick: () => router.push(`/products/${row.id}`) },
              { default: () => t('common.edit') }
            ),
            h(
              NPopconfirm,
              {
                onPositiveClick: () => deleteProduct(row)
              },
              {
                trigger: () =>
                  h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => t('common.delete') }),
                default: () => t('page.products.deleteConfirm')
              }
            )
          ]
        }
      )
  }
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

function goPage(p: number) {
  page.value = p;
  loadProducts();
}

async function batchStatus(target: string) {
  if (!checkedRowKeys.value.length) {
    message.warning(t('page.products.selectProduct'));
    return;
  }
  try {
    const res = await post('/api/admin/v1/products/batch-status', {
      ids: checkedRowKeys.value,
      status: target
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
      headers: token ? { Authorization: `Bearer ${token}` } : {}
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
        <NInput
          v-model:value="search"
          :placeholder="$t('page.products.searchPlaceholder')"
          clearable
          style="width: 260px"
          @keyup.enter="handleQuery"
        />
        <NSelect
          v-model:value="category"
          :options="categoryOptions"
          :placeholder="$t('page.products.allCategories')"
          clearable
          style="width: 160px"
        />
        <NSelect
          v-model:value="status"
          :options="statusOptions"
          :placeholder="$t('page.products.allStatus')"
          clearable
          style="width: 140px"
        />
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
        <NButton
          size="small"
          type="success"
          secondary
          :disabled="!checkedRowKeys.length"
          @click="batchStatus('active')"
        >
          {{ $t('page.products.batchEnable') }}
        </NButton>
        <NButton
          size="small"
          type="warning"
          secondary
          :disabled="!checkedRowKeys.length"
          @click="batchStatus('inactive')"
        >
          {{ $t('page.products.batchDisable') }}
        </NButton>
        <NButton size="small" type="error" secondary :disabled="!checkedRowKeys.length" @click="batchDelete">
          {{ $t('page.products.batchDelete') }}
        </NButton>
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
            :options="[
              { label: '10', value: 10 },
              { label: '20', value: 20 },
              { label: '50', value: 50 }
            ]"
            style="width: 80px"
            @update:value="
              page = 1;
              loadProducts();
            "
          />
          <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
        </NSpace>
      </div>
    </NCard>

    <NModal v-model:show="showImportModal" preset="card" :title="$t('page.products.importResult')" style="width: 720px">
      <NSpace vertical>
        <NSpace>
          <NTag type="success" :bordered="false">
            {{ $t('page.products.importCreated') }}: {{ importResult?.created ?? 0 }}
          </NTag>
          <NTag type="info" :bordered="false">
            {{ $t('page.products.importUpdated') }}: {{ importResult?.updated ?? 0 }}
          </NTag>
          <NTag :type="(importResult?.failed ?? 0) > 0 ? 'error' : 'default'" :bordered="false">
            {{ $t('page.products.importFailed') }}: {{ importResult?.failed ?? 0 }}
          </NTag>
        </NSpace>
        <NDataTable
          v-if="importResult?.errors?.length"
          :columns="errorColumns"
          :data="importResult.errors"
          size="small"
          :bordered="false"
        />
      </NSpace>
    </NModal>

    <NDrawer v-model:show="showSkuDrawer" :width="760" placement="right">
      <NDrawerContent :title="`SKU 库存编辑 — ${skuProduct?.name ?? ''}（${skuProduct?.sku ?? ''}）`" closable>
        <div class="flex flex-col" style="height: 100%">
          <NDataTable
            :columns="variantColumns"
            :data="variants"
            :loading="variantLoading"
            size="small"
            :bordered="false"
            :row-key="row => row.id"
            style="flex: 1; min-height: 0"
          />

          <NCard
            v-if="editingIndex >= 0 || addingVariant"
            :bordered="true"
            size="small"
            :title="variantForm.id ? '编辑 SKU' : '新增 SKU'"
            class="mt-4"
          >
            <NForm label-placement="left" label-width="80" size="small">
              <div class="flex flex-wrap" style="row-gap: 0">
                <div style="width: 50%">
                  <NFormItem label="名称">
                    <NInput v-model:value="variantForm.name" placeholder="如：红色 / M 码" />
                  </NFormItem>
                </div>
                <div style="width: 50%">
                  <NFormItem label="SKU">
                    <NInput v-model:value="variantForm.sku" placeholder="留空自动生成，如 PET-1001-BLK-M" />
                  </NFormItem>
                </div>
                <div style="width: 50%">
                  <NFormItem label="价格">
                    <NInputNumber v-model:value="variantForm.price" :min="0" :precision="2" style="width: 100%" />
                  </NFormItem>
                </div>
                <div style="width: 50%">
                  <NFormItem label="成本">
                    <NInputNumber v-model:value="variantForm.cost" :min="0" :precision="2" style="width: 100%" />
                  </NFormItem>
                </div>
                <div style="width: 50%">
                  <NFormItem label="库存">
                    <NInputNumber v-model:value="variantForm.inventory" :min="0" style="width: 100%" />
                  </NFormItem>
                </div>
                <div style="width: 50%">
                  <NFormItem label="状态">
                    <NSelect v-model:value="variantForm.status" :options="variantStatusOptions" style="width: 100%" />
                  </NFormItem>
                </div>
                <div style="width: 50%">
                  <NFormItem label="默认"><NSwitch v-model:value="variantForm.is_default" /></NFormItem>
                </div>
              </div>

              <div class="mb-1">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium">规格（用于自动生成 SKU 短码）</span>
                  <NButton size="tiny" quaternary type="primary" @click="addSpecRow">+ 添加规格</NButton>
                </div>
                <div v-if="variantForm.specRows.length" class="flex flex-col gap-1">
                  <div v-for="(row, idx) in variantForm.specRows" :key="idx" class="flex items-center gap-2">
                    <NInput v-model:value="row.key" placeholder="规格名，如 color" style="width: 40%" />
                    <NInput v-model:value="row.value" placeholder="规格值，如 black" style="width: 45%" />
                    <NButton size="tiny" quaternary type="error" @click="removeSpecRow(idx)">删除</NButton>
                  </div>
                </div>
                <div v-else class="text-xs text-gray-400">未填写规格时 SKU 仅基于货号生成</div>
              </div>
              <NSpace justify="end" class="mt-2">
                <NButton size="small" @click="cancelEditVariant">取消</NButton>
                <NButton size="small" type="primary" :loading="variantSaving" @click="saveVariant">保存</NButton>
              </NSpace>
            </NForm>
          </NCard>

          <div class="flex justify-between items-center mt-4">
            <span class="text-sm text-gray-500">共 {{ variants.length }} 个 SKU</span>
            <NButton size="small" type="primary" secondary @click="startAddVariant">新增 SKU</NButton>
          </div>
        </div>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
