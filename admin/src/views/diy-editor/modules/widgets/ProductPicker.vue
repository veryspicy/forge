<template>
  <div class="w-full">
    <NButton size="small" block dashed @click="open">
      <template #icon><SvgIcon icon="mdi:package-variant" /></template>
      {{ multiple ? `选择商品（已选 ${selectedIds.length} 个）` : selectedIds.length ? '已选 1 个商品' : '选择商品' }}
    </NButton>

    <NModal v-model:show="show" preset="card" title="选择商品" style="width:760px">
      <div class="mb-3 flex gap-2">
        <NInput v-model:value="search" placeholder="搜索商品名称 / SKU" clearable @keyup.enter="fetchProducts" />
        <NButton type="primary" @click="fetchProducts">{{ $t('common.search') }}</NButton>
      </div>
      <NDataTable
        :columns="columns"
        :data="products"
        :loading="loading"
        :bordered="false"
        size="small"
        :row-key="(row: any) => row.id"
        :checked-row-keys="checkedKeys"
        @update:checked-row-keys="onCheck"
      />
      <div class="mt-3 flex items-center justify-between">
        <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
        <NSpace>
          <NButton @click="show = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" @click="confirm">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </div>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue';
import { NButton, NDataTable, NImage, NInput, NModal, NPagination, NSpace } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { get } from '@/service/api/helper';

const props = withDefaults(
  defineProps<{
    modelValue?: string | string[];
    multiple?: boolean;
  }>(),
  { multiple: false }
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | string[]): void;
}>();

const show = ref(false);
const loading = ref(false);
const search = ref('');
const products = ref<any[]>([]);
const page = ref(1);
const total = ref(0);
const pageSize = 10;

const selectedIds = computed<string[]>(() => {
  if (props.multiple) return Array.isArray(props.modelValue) ? [...props.modelValue] : [];
  return props.modelValue ? [String(props.modelValue)] : [];
});

const checkedKeys = ref<(string | number)[]>([]);

const columns = computed<DataTableColumns<any>>(() => [
  { type: 'selection', multiple: props.multiple } as any,
  {
    title: 'Image',
    key: 'image',
    width: 60,
    render: row =>
      row.images?.[0]
        ? h(NImage, { src: row.images[0], width: 36, height: 36, style: { objectFit: 'cover', borderRadius: '4px' } })
        : '--'
  },
  { title: 'Name', key: 'name', ellipsis: { tooltip: true } },
  { title: 'SKU', key: 'sku', width: 120 },
  { title: 'Price', key: 'price', width: 90, render: row => `$${row.price}` },
  { title: 'Category', key: 'category', width: 110 }
]);

function open() {
  checkedKeys.value = [...selectedIds.value];
  show.value = true;
  page.value = 1;
  fetchProducts();
}

async function fetchProducts() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (search.value) params.search = search.value;
    const res = await get('/api/admin/v1/products/', params);
    products.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

function goPage(p: number) {
  page.value = p;
  fetchProducts();
}

function onCheck(keys: (string | number)[]) {
  checkedKeys.value = props.multiple ? keys : keys.slice(-1);
}

function confirm() {
  if (props.multiple) {
    emit('update:modelValue', checkedKeys.value.map(String));
  } else {
    emit('update:modelValue', checkedKeys.value.length ? String(checkedKeys.value[0]) : '');
  }
  show.value = false;
}
</script>
