<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <NSpace>
        <NInput v-model:value="search" :placeholder="$t('common.search')" style="width:200px" @keyup.enter="fetch" />
        <NSelect v-model:value="category" :options="categoryOptions" :placeholder="$t('page.products.allCategories')" clearable @update:value="fetch" />
      </NSpace>
      <NButton type="primary" @click="$router.push('/products/new')">{{ $t('common.add') }}</NButton>
    </div>

    <NDataTable :columns="columns" :data="products" :loading="loading" :bordered="false" size="small" />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { NButton, NDataTable, NImage, NInput, NPagination, NSelect, NSpace, NTag } from 'naive-ui';
import { get } from '@/service/api/helper';
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

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (search.value) params.search = search.value;
    if (category.value) params.category = category.value;
    const res = await get('/api/admin/v1/products/', { params });
    products.value = res.data?.items || res.data || [];
    total.value = res.data?.total || 0;
  } finally { loading.value = false; }
}

function goPage(p: number) { page.value = p; fetch(); }

onMounted(fetch);
</script>
