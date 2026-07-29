<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <NInput v-model:value="search" :placeholder="$t('common.search')" style="width:220px" @keyup.enter="fetch" />
      <NSelect v-model:value="statusFilter" :options="statusOptions" :placeholder="$t('page.orders.allStatus')" clearable style="width:160px" @update:value="fetch" />
    </div>

    <NDataTable :columns="columns" :data="orders" :loading="loading" :bordered="false" size="small" />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { NButton, NDataTable, NInput, NPagination, NSelect, NTag } from 'naive-ui';
import { get } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const router = useRouter();
const { t } = useI18n();
const loading = ref(false);
const search = ref('');
const statusFilter = ref<string | null>(null);
const orders = ref<any[]>([]);
const page = ref(1);
const total = ref(0);
const pageSize = 20;

const statusOptions = ['PAID', 'PROCESSING', 'PROCURING', 'PROCURE_FAILED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED']
  .map(s => ({ label: s, value: s }));

function statusType(s: string): any {
  const map: Record<string, any> = { PAID: 'info', PROCESSING: 'warning', PROCURING: 'warning', PROCURE_FAILED: 'error', SHIPPED: 'info', DELIVERED: 'success', CANCELLED: 'default', REFUNDED: 'error' };
  return map[s] || 'default';
}

const columns: DataTableColumns<any> = [
  { title: t('page.orders.orderNumber'), key: 'order_number', render: row => (row.order_number || '').slice(0, 12) + '...' },
  { title: t('common.userId'), key: 'user_id', render: row => (row.user_id || '').slice(0, 8) + '...' },
  { title: t('page.orders.total'), key: 'total', render: row => `$${row.total}` },
  {
    title: t('common.status'), key: 'status',
    render: row => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => row.status }),
  },
  { title: t('common.items'), key: 'items', render: row => row.items?.length || 0 },
  { title: t('page.orders.date'), key: 'created_at', render: row => row.created_at ? new Date(row.created_at).toLocaleDateString() : '-' },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NButton, { size: 'small', onClick: () => router.push(`/orders/${row.id}`) }, { default: () => t('common.detail') }),
  },
];

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (search.value) params.search = search.value;
    if (statusFilter.value) params.status = statusFilter.value;
    const res = await get('/api/admin/v1/orders/', { params });
    orders.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally { loading.value = false; }
}

function goPage(p: number) { page.value = p; fetch(); }

onMounted(fetch);
</script>
