<script setup lang="ts">
import { computed, ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import {
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NInput,
  NPagination,
  NPopconfirm,
  NSelect,
  NTag,
  NTooltip,
  useMessage
} from 'naive-ui';
import { get, post, del } from '@/service/api/helper';
import { localStg } from '@/utils/storage';
import { useAuthStore } from '@/store/modules/auth';
import type { DataTableColumns } from 'naive-ui';

const router = useRouter();
const authStore = useAuthStore();
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
  if (mode === 'dropship') return t('page.orders.fulfillmentDropship');
  if (mode === 'mixed') return t('page.orders.fulfillmentMixed');
  return t('page.orders.fulfillmentSelfPurchase');
}

/** 客户管理页仅 super_admin / admin 可进，其他角色不渲染外链，避免跳转被路由守卫拦截 */
const canOpenCustomer = computed(() => {
  const roles = authStore.userInfo.roles || [];
  return roles.includes('super_admin') || roles.includes('admin');
});

/** 跳转客户管理页并定位到该订单所属客户（列表按邮箱过滤 + 直接打开客户资料抽屉） */
function openCustomer(row: any) {
  const query: Record<string, string> = {};
  if (row.user_id) query.user_id = String(row.user_id);
  if (row.email) query.email = String(row.email);
  if (!Object.keys(query).length) return;
  router.push({ path: '/customers', query });
}

/** 归档（后台删除）入口仅对持有 orders:archive 的角色渲染；super_admin 走权限通配 '*' */
const canArchive = computed(() => {
  const perms = authStore.userInfo.permissions || [];
  return perms.includes('*') || perms.includes('orders:archive');
});

/** 列表视图：默认仅看进行中记录；切到「已归档」时列出 admin_archived_at 已置位的记录 */
const archivedView = ref(false);
/** NSelect 仅接受字符串值，这里做布尔语义到字符串视图的映射 */
const viewValue = computed(() => (archivedView.value ? 'archived' : 'active'));
const viewOptions = computed(() => [
  { label: t('page.archive.viewActive'), value: 'active' },
  { label: t('page.archive.viewArchived'), value: 'archived' }
]);

/** 归档/恢复选中项；行级操作复用同一套请求逻辑（单条走 DELETE，多条走批量接口） */
const checkedKeys = ref<string[]>([]);
const archiving = ref(false);

function switchView(value: string) {
  archivedView.value = value === 'archived';
  checkedKeys.value = [];
  page.value = 1;
  fetch();
}

function uniq(list: (string | number)[]) {
  return Array.from(new Set(list.map(v => String(v ?? '')).filter(Boolean)));
}

/** 归档/恢复结果统一提示（后端返回 archived|restored / skipped / missing） */
function notifyArchiveResult(data: any, mode: 'archive' | 'restore') {
  const target = t('page.archive.targetOrder');
  const count = Number((mode === 'archive' ? data.archived : data.restored) || 0);
  const skipped = Number(data.skipped || 0);
  const missing: string[] = data.missing || [];
  const msg = (key: string, n: number) => t(`page.archive.${key}`, { n, target });
  if (!count && !skipped && !missing.length) {
    message.info(t(mode === 'archive' ? 'page.archive.empty' : 'page.archive.restoreEmpty', { target }));
  }
  if (count) message.success(msg(mode === 'archive' ? 'done' : 'restoreDone', count));
  if (skipped) message.info(msg(mode === 'archive' ? 'skipped' : 'restoreSkipped', skipped));
  if (missing.length) message.warning(msg(mode === 'archive' ? 'missing' : 'restoreMissing', missing.length));
}

async function archiveOrders(numbers: string[]) {
  const targets = uniq(numbers);
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res =
      targets.length === 1
        ? await del(`/api/admin/v1/orders/${encodeURIComponent(targets[0])}`)
        : await post('/api/admin/v1/orders/archive', { order_numbers: targets });
    notifyArchiveResult(res.data || {}, 'archive');
    checkedKeys.value = [];
    await fetch();
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('page.archive.failed'));
  } finally {
    archiving.value = false;
  }
}

async function restoreOrders(numbers: string[]) {
  const targets = uniq(numbers);
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res = await post('/api/admin/v1/orders/unarchive', { order_numbers: targets });
    notifyArchiveResult(res.data || {}, 'restore');
    checkedKeys.value = [];
    await fetch();
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('page.archive.restoreFailed'));
  } finally {
    archiving.value = false;
  }
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
  {
    title: t('common.userId'),
    key: 'user_id',
    render: row => {
      const uid = String(row.user_id || '');
      const label = uid ? `${uid.slice(0, 8)}...` : '-';
      if (!uid || !canOpenCustomer.value) return label;
      return h(
        NButton,
        { text: true, type: 'primary', size: 'small', onClick: () => openCustomer(row) },
        { default: () => label }
      );
    }
  },
  { title: t('page.orders.total'), key: 'total', render: row => `$${row.total}` },
  {
    title: t('common.status'),
    key: 'status',
    render: row => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  {
    title: t('page.orders.fulfillmentMode'),
    key: 'fulfillment_mode',
    render: row => fulfillmentModeLabel(row.fulfillment_mode)
  },
  {
    title: t('page.orders.paymentRefund'),
    key: 'payment_status',
    render: row => {
      const refunded = Number(row.refunded_amount || 0);
      const suffix =
        refunded > 0 ? t('page.orders.refundedSuffix', { amount: refunded.toFixed(2) }) : '';
      return `${paymentLabel(row.payment_status)}${suffix}`;
    }
  },
  {
    // 表头带悬浮说明：口径为「售后申请总数（含已驳回/已关闭）+ 进行中数量标红」
    title: () =>
      h(
        NTooltip,
        { trigger: 'hover', style: 'max-width: 340px' },
        {
          trigger: () =>
            h(
              'span',
              { style: 'cursor: help; border-bottom: 1px dashed var(--n-border-color)' },
              t('page.orders.afterSales')
            ),
          default: () => t('page.orders.afterSalesTip')
        }
      ),
    key: 'returns_summary',
    render: row => {
      const summary = row.returns_summary;
      if (!summary || !summary.total) return t('page.orders.afterSalesNone');
      const pending = Number(summary.open || 0);
      const label = `${summary.total}${pending ? ` · ${t('page.orders.afterSalesPending', { count: pending })}` : ''}`;
      return h(
        NTag,
        {
          size: 'small',
          type: pending ? 'error' : 'info',
          style: 'cursor: pointer',
          onClick: () => router.push({ path: '/returns', query: { keyword: row.order_number } })
        },
        { default: () => label }
      );
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
        ),
        canArchive.value
          ? h(
              NPopconfirm,
              {
                onPositiveClick: () =>
                  archivedView.value ? restoreOrders([row.order_number]) : archiveOrders([row.order_number])
              },
              {
                trigger: () =>
                  h(
                    NButton,
                    { size: 'small', quaternary: true, type: archivedView.value ? 'primary' : 'error' },
                    { default: () => t(archivedView.value ? 'page.archive.restore' : 'page.archive.action') }
                  ),
                default: () =>
                  t(archivedView.value ? 'page.archive.restoreConfirm' : 'page.archive.confirm', {
                    target: t('page.archive.targetOrder')
                  })
              }
            )
          : null
      ])
  }
];

/** 选择列仅在具备归档权限时出现，无权角色看不到多选与批量入口 */
const selectionColumn: DataTableColumns<any>[number] = {
  type: 'selection',
  disabled: (row: any) => !row.order_number
};

const tableColumns = computed<DataTableColumns<any>>(() =>
  canArchive.value ? [selectionColumn, ...columns] : columns
);

function rowKey(row: any) {
  return String(row?.order_number || '');
}

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
    if (archivedView.value) params.archived = true;
    const res = await get('/api/admin/v1/orders/', params);
    orders.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

const debouncedFetch = useDebounceFn(() => {
  page.value = 1;
  fetch();
}, 400);

/** 立即搜索：清空关键词 / 回车 / 切换状态时调用，取消防抖中挂起的请求 */
function resetAndFetch() {
  (debouncedFetch as any).cancel?.();
  page.value = 1;
  fetch();
}

/**
 * 输入即触发：停止输入 400ms 自动搜索；清空关键词立即回到全量列表。
 * 通过 NInput 的 @update:value 直接驱动，避免依赖 watch 时序。
 */
function onSearchInput(value: string | null) {
  if (!String(value ?? '').trim()) resetAndFetch();
  else debouncedFetch();
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
const purchaseStatusOptions = computed(() => [
  { label: t('page.orders.procurementPending'), value: 'pending' },
  { label: t('page.orders.procurementRequested'), value: 'requested' },
  { label: t('page.orders.procurementReceived'), value: 'received' },
  { label: t('page.orders.procurementAll'), value: 'all' }
]);

function procurementStatusLabel(status?: string | null): string {
  if (status === 'received') return t('page.orders.procurementReceived');
  if (status === 'requested') return t('page.orders.procurementRequested');
  return t('page.orders.procurementPending');
}

const purchaseColumns: DataTableColumns<any> = [
  { title: t('page.orders.orderNumber'), key: 'order_number' },
  { title: t('common.name'), key: 'name' },
  { title: t('page.orders.supplierSku'), key: 'supplier_sku', render: row => row.supplier_sku || '-' },
  { title: t('common.sku'), key: 'sku' },
  { title: t('common.quantity'), key: 'quantity' },
  {
    title: t('page.orders.procurementStatus'),
    key: 'procurement_status',
    render: row => procurementStatusLabel(row.procurement_status)
  },
  {
    title: t('page.orders.procurementRequestedAt'),
    key: 'procurement_requested_at',
    render: row => (row.procurement_requested_at ? new Date(row.procurement_requested_at).toLocaleString() : '-')
  },
  { title: t('page.orders.destination'), key: 'destination' },
  {
    title: t('page.orders.date'),
    key: 'created_at',
    render: row => (row.created_at ? new Date(row.created_at).toLocaleDateString() : '-')
  }
];

/** 分组卡标题：供应商名 + 项数/件数（未指定供应商走 i18n 兜底） */
function purchaseGroupTitle(g: any) {
  return t('page.orders.supplierSummary', {
    name: g.supplier_name || t('page.orders.unspecifiedSupplier'),
    count: g.item_count,
    qty: g.total_quantity
  });
}

async function loadPurchaseList() {
  purchaseLoading.value = true;
  try {
    const res = await get('/api/admin/v1/orders/purchase-list', { status: purchaseStatus.value });
    purchaseGroups.value = res.data?.groups || [];
  } catch {
    message.error(t('page.orders.purchaseLoadFailed'));
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
    message.error(t('page.orders.purchaseExportFailed'));
  }
}

onMounted(fetch);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <NInput
        v-model:value="search"
        :placeholder="$t('common.search')"
        style="width: 220px"
        clearable
        :input-props="{ autocomplete: 'off' }"
        @update:value="onSearchInput"
        @keyup.enter="resetAndFetch"
      />
      <NSelect
        v-model:value="statusFilter"
        :options="statusOptions"
        :placeholder="$t('page.orders.allStatus')"
        clearable
        style="width: 160px"
        @update:value="fetch"
      />
      <NSelect
        :value="viewValue"
        :options="viewOptions"
        style="width: 140px"
        @update:value="switchView"
      />
      <NButton v-if="!archivedView" secondary :loading="loading" @click="exportCsv">
        {{ $t('page.orders.export') }}
      </NButton>
      <NButton secondary type="primary" @click="openPurchaseList">{{ $t('page.orders.purchaseList') }}</NButton>
      <NPopconfirm
        v-if="canArchive"
        @positive-click="archivedView ? restoreOrders(checkedKeys) : archiveOrders(checkedKeys)"
      >
        <template #trigger>
          <NButton
            :type="archivedView ? 'primary' : 'error'"
            secondary
            :disabled="!checkedKeys.length"
            :loading="archiving"
          >
            {{ archivedView ? $t('page.archive.restoreBatch') : $t('page.archive.actionBatch')
            }}{{ checkedKeys.length ? ' (' + checkedKeys.length + ')' : '' }}
          </NButton>
        </template>
        {{
          archivedView
            ? $t('page.archive.restoreConfirmBatch', {
              n: checkedKeys.length,
              target: $t('page.archive.targetOrder')
            })
            : $t('page.archive.confirmBatch', { n: checkedKeys.length, target: $t('page.archive.targetOrder') })
        }}
      </NPopconfirm>
    </div>

    <NDataTable
      v-model:checked-row-keys="checkedKeys"
      :row-key="rowKey"
      :columns="tableColumns"
      :data="orders"
      :loading="loading"
      :bordered="false"
      size="small"
    />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>

    <NDrawer v-model:show="showPurchase" :width="920" placement="right">
      <NDrawerContent :title="$t('page.orders.purchaseListTitle')" closable>
        <div class="mb-3 flex items-center justify-between gap-3">
          <NSelect
            v-model:value="purchaseStatus"
            :options="purchaseStatusOptions"
            style="width: 140px"
            @update:value="loadPurchaseList"
          />
          <NButton size="small" secondary :loading="purchaseLoading" @click="exportPurchaseList">
            {{ $t('page.orders.exportPurchase') }}
          </NButton>
        </div>
        <div v-if="purchaseGroups.length" class="flex flex-col gap-3">
          <NCard
            v-for="g in purchaseGroups"
            :key="g.supplier_id || 'UNASSIGNED'"
            size="small"
            :title="purchaseGroupTitle(g)"
          >
            <NDataTable :columns="purchaseColumns" :data="g.items" :bordered="false" size="small" />
          </NCard>
        </div>
        <NEmpty v-else :description="$t('page.orders.purchaseEmpty')" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
