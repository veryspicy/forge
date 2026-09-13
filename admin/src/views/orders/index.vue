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
  NEmpty,
  NInput,
  NPagination,
  NSelect,
  NTag,
  useMessage
} from 'naive-ui';
import { get } from '@/service/api/helper';
import { localStg } from '@/utils/storage';
import type { DataTableColumns } from 'naive-ui';

const router = useRouter();
const { t } = useI18n();
const message = useMessage();
const loading = ref(false);
const search = ref('');
const statusFilter = ref<string | null>(null);
const orders = ref<any[]>([]);
const page = ref(1);
const total = ref(0);
const pageSize = 20;

const ORDER_STATUS_LABEL_KEYS: Record<string, string> = {
  pending: 'statusPending',
  confirmed: 'statusConfirmed',
  processing: 'statusProcessing',
  procuring: 'statusProcuring',
  procure_failed: 'statusProcureFailed',
  shipped: 'statusShipped',
  delivered: 'statusDelivered',
  cancelled: 'statusCancelled',
  refunded: 'statusRefunded'
};

const PAYMENT_STATUS_LABEL_KEYS: Record<string, string> = {
  unpaid: 'paymentUnpaid',
  paid: 'paymentPaid',
  partially_refunded: 'paymentPartiallyRefunded',
  refunded: 'paymentRefunded',
  failed: 'paymentFailed'
};

function localizeStatus(map: Record<string, string>, value?: string | null): string {
  const key = String(value || '');
  if (!key) return '-';
  const i18nKey = map[key];
  return i18nKey ? t(`page.ordersDetail.${i18nKey}`) : key;
}

function statusLabel(value?: string | null): string {
  return localizeStatus(ORDER_STATUS_LABEL_KEYS, value);
}

function paymentLabel(value?: string | null): string {
  return localizeStatus(PAYMENT_STATUS_LABEL_KEYS, value);
}

const statusOptions = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'].map(
  s => ({ label: statusLabel(s), value: s })
);

function statusType(s: string): any {
  const map: Record<string, any> = {
    pending: 'default',
    confirmed: 'info',
    processing: 'warning',
    procuring: 'warning',
    procure_failed: 'error',
    shipped: 'info',
    delivered: 'success',
    cancelled: 'default',
    refunded: 'error'
  };
  return map[s] || 'default';
}

function fulfillmentModeLabel(mode?: string | null): string {
  if (mode === 'dropship') return '一件代发';
  if (mode === 'mixed') return '混合';
  return '自采购';
}

const columns: DataTableColumns<any> = [
  {
    title: t('page.orders.orderNumber'),
    key: 'order_number',
    render: row =>
      h(
        NButton,
        { text: true, type: 'primary', size: 'small', onClick: () => router.push(`/orders/${row.order_number}`) },
        { default: () => row.order_number || '-' }
      )
  },
  { title: t('common.userId'), key: 'user_id', render: row => (row.user_id || '').slice(0, 8) + '...' },
  { title: t('page.orders.total'), key: 'total', render: row => `$${row.total}` },
  {
    title: t('common.status'),
    key: 'status',
    render: row => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  {
    title: '履约模式',
    key: 'fulfillment_mode',
    render: row => fulfillmentModeLabel(row.fulfillment_mode)
  },
  {
    title: '支付/退款',
    key: 'payment_status',
    render: row => {
      const refunded = Number(row.refunded_amount || 0);
      const suffix = refunded > 0 ? ` / 已退 $${refunded.toFixed(2)}` : '';
      return `${paymentLabel(row.payment_status)}${suffix}`;
    }
  },
  { title: t('common.items'), key: 'items', render: row => row.items?.length || 0 },
  {
    title: t('page.orders.date'),
    key: 'created_at',
    render: row => (row.created_at ? new Date(row.created_at).toLocaleDateString() : '-')
  },
  {
    title: t('page.orders.actions'),
    key: 'actions',
    render: row =>
      h('div', { class: 'flex items-center gap-2' }, [
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'primary',
            onClick: () => copyText(row.order_number)
          },
          { default: () => t('page.orders.copyOrderNumber') }
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'primary',
            onClick: () => copyText(row.email, true)
          },
          { default: () => t('page.orders.copyEmail') }
        )
      ])
  }
];

async function copyText(value: string | undefined | null, isEmail = false) {
  const text = (value || '').trim();
  if (!text) {
    if (isEmail) message.warning(t('page.orders.copyEmailEmpty'));
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    message.success(t('page.orders.copySuccess'));
  } catch {
    message.error(t('page.orders.copyFailed'));
  }
}

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (search.value) params.search = search.value;
    if (statusFilter.value) params.status = statusFilter.value;
    const res = await get('/api/admin/v1/orders/', params);
    orders.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

function goPage(p: number) {
  page.value = p;
  fetch();
}

async function exportCsv() {
  try {
    const params = new URLSearchParams();
    if (search.value) params.set('search', search.value);
    if (statusFilter.value) params.set('status', statusFilter.value);
    const token = localStg.get('token');
    const res = await window.fetch(`/api/admin/v1/orders/export?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) throw new Error('export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `orders_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    message.error(t('page.orders.exportFailed'));
  }
}

/* ===== 待采购清单（一件代发行，按供应商聚合） ===== */
const showPurchase = ref(false);
const purchaseLoading = ref(false);
const purchaseGroups = ref<any[]>([]);
const purchaseStatus = ref<string>('pending');
const purchaseStatusOptions = [
  { label: '未采购', value: 'pending' },
  { label: '采购中', value: 'requested' },
  { label: '已入库', value: 'received' },
  { label: '全部', value: 'all' }
];

function procurementStatusLabel(status?: string | null): string {
  if (status === 'received') return '已入库';
  if (status === 'requested') return '采购中';
  return '未采购';
}

const purchaseColumns: DataTableColumns<any> = [
  { title: t('page.orders.orderNumber'), key: 'order_number' },
  { title: t('common.name'), key: 'name' },
  { title: '供应商 SKU', key: 'supplier_sku', render: row => row.supplier_sku || '-' },
  { title: t('common.sku'), key: 'sku' },
  { title: t('common.quantity'), key: 'quantity' },
  {
    title: '采购状态',
    key: 'procurement_status',
    render: row => procurementStatusLabel(row.procurement_status)
  },
  {
    title: '推送时间',
    key: 'procurement_requested_at',
    render: row => (row.procurement_requested_at ? new Date(row.procurement_requested_at).toLocaleString() : '-')
  },
  { title: '收货地', key: 'destination' },
  {
    title: t('page.orders.date'),
    key: 'created_at',
    render: row => (row.created_at ? new Date(row.created_at).toLocaleDateString() : '-')
  }
];

async function loadPurchaseList() {
  purchaseLoading.value = true;
  try {
    const res = await get('/api/admin/v1/orders/purchase-list', { status: purchaseStatus.value });
    purchaseGroups.value = res.data?.groups || [];
  } catch {
    message.error('待采购清单加载失败');
  } finally {
    purchaseLoading.value = false;
  }
}

function openPurchaseList() {
  showPurchase.value = true;
  loadPurchaseList();
}

async function exportPurchaseList() {
  try {
    const token = localStg.get('token');
    const params = new URLSearchParams({ status: purchaseStatus.value });
    const res = await window.fetch(`/api/admin/v1/orders/purchase-list/export?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) throw new Error('export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `purchase_list_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    message.error('待采购清单导出失败');
  }
}

onMounted(fetch);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <NInput v-model:value="search" :placeholder="$t('common.search')" style="width: 220px" @keyup.enter="fetch" />
      <NSelect
        v-model:value="statusFilter"
        :options="statusOptions"
        :placeholder="$t('page.orders.allStatus')"
        clearable
        style="width: 160px"
        @update:value="fetch"
      />
      <NButton secondary :loading="loading" @click="exportCsv">{{ $t('page.orders.export') }}</NButton>
      <NButton secondary type="primary" @click="openPurchaseList">待采购清单</NButton>
    </div>

    <NDataTable :columns="columns" :data="orders" :loading="loading" :bordered="false" size="small" />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>

    <NDrawer v-model:show="showPurchase" :width="920" placement="right">
      <NDrawerContent title="待采购清单（代发行）" closable>
        <div class="mb-3 flex items-center justify-between gap-3">
          <NSelect
            v-model:value="purchaseStatus"
            :options="purchaseStatusOptions"
            style="width: 140px"
            @update:value="loadPurchaseList"
          />
          <NButton size="small" secondary :loading="purchaseLoading" @click="exportPurchaseList">导出 CSV</NButton>
        </div>
        <div v-if="purchaseGroups.length" class="flex flex-col gap-3">
          <NCard
            v-for="g in purchaseGroups"
            :key="g.supplier_id || 'UNASSIGNED'"
            size="small"
            :title="`${g.supplier_name || '未指定供应商'}（${g.item_count} 项 / ${g.total_quantity} 件）`"
          >
            <NDataTable :columns="purchaseColumns" :data="g.items" :bordered="false" size="small" />
          </NCard>
        </div>
        <NEmpty v-else description="当前没有待采购的代发行" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
