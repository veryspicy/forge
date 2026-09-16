<script setup lang="ts">
import { h, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NCheckbox,
  NDataTable,
  NEmpty,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSpace,
  NSpin,
  NTag
} from 'naive-ui';
import { useI18n } from 'vue-i18n';
import { get, post } from '@/service/api/helper';
import {
  ORDER_CANCEL_REASON_DEFAULT,
  ORDER_CANCEL_REASON_OPTIONS,
  ORDER_REFUND_REASON_DEFAULT,
  ORDER_REFUND_REASON_OPTIONS,
  ORDER_REJECT_REASON_OPTIONS,
  returnReasonLabel
} from '@/constants/aftersalesReasons';
import type { DataTableColumns } from 'naive-ui';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const order = ref<any>(null);
const loading = ref(true);

const showReview = ref(false);
const reviewApprove = ref(true);
const reviewReason = ref('');
const reviewBy = ref('');
const showProcure = ref(false);
const procureTargets = ref<any[]>([]);
const procureSupplierId = ref('');
const procureSku = ref('');
const procureCost = ref(0);
const showShip = ref(false);
const shipPackages = ref<Array<{ carrier: string; tracking_number: string; supplier_id: string }>>([]);
const showRefund = ref(false);
const refundReason = ref('');
const refundLines = ref<Array<{ id: string; name: string; quantity: number; refundable: number }>>([]);
const refundShipping = ref(false);
const refundRestock = ref(false);
// 退款幂等键：打开退款弹窗时生成，重复提交不会二次扣款
const refundIdempotencyKey = ref('');
const showCancel = ref(false);
const cancelReason = ref('');
const cancelRefund = ref(true);
const actionError = ref('');
const actionLoading = ref(false);

/** 售后动作原因：预设可选 + 允许自定义输入（NSelect tag） */
const toReasonOptions = (values: string[]) => values.map(value => ({ label: value, value }));
const rejectReasonOptions = toReasonOptions(ORDER_REJECT_REASON_OPTIONS);
const refundReasonOptions = toReasonOptions(ORDER_REFUND_REASON_OPTIONS);
const cancelReasonOptions = toReasonOptions(ORDER_CANCEL_REASON_OPTIONS);

// 退款按资金余额判定，与订单履约状态解耦（行业：Shopify refundCreate，部分退款不阻断剩余行发货）
function refundableAmount(): number {
  return Number(order.value?.refundable_amount || 0);
}
/** 是否还有可退余额：退款类入口（取消 / 审核拒绝 / 仅退款）的显隐基准 */
function hasRefundableBalance(): boolean {
  return refundableAmount() > 0.001;
}
/** 仅退款入口：发货前只开放「部分退款」（全额退款走取消 / 审核拒绝等终止入口）；发货后是唯一资金入口，始终开放 */
function canRefund(): boolean {
  if (!hasRefundableBalance()) return false;
  const s = order.value?.status || '';
  if (s === 'shipped' || s === 'delivered') return true;
  return refundableAmount() < Number(order.value?.total || 0) - 0.01;
}
/** 取消入口：待审核（confirmed）阶段的终止动作是审核拒绝，不重复提供取消；待付款与审核通过后仍可取消 */
function canCancel(): boolean {
  return ['pending', 'processing'].includes(order.value?.status || '');
}
/** 风控硬门禁：订单必须审核通过才可发货（后端同步硬校验，不再依赖站点开关） */
function shipBlocked(): boolean {
  return !order.value?.review_approved;
}
function canShip(): boolean {
  if (shipBlocked()) return false;
  return ['confirmed', 'processing'].includes(order.value?.status || '');
}
/** 退款幂等键：每次打开退款弹窗生成一次，重复点击提交不会二次扣款 */
function newRefundIdempotencyKey(): string {
  const uuid = (window.crypto as any)?.randomUUID?.();
  return uuid ? `admin-refund:${uuid}` : `admin-refund:${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
function dropshipRows(): any[] {
  return (order.value?.items || []).filter((i: any) => i.fulfillment_mode === 'dropship');
}
function procurementStatusLabel(status?: string | null): string {
  if (status === 'received') return '已入库';
  if (status === 'requested') return '采购中';
  return '未采购';
}

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

function money(v: any): string {
  const n = Number(v || 0);
  return `$${n.toFixed(2)}`;
}

function fmtTime(v?: string | null): string {
  if (!v) return '-';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString();
}

function paymentStatusType(s: string): any {
  const map: Record<string, any> = {
    paid: 'success',
    refunded: 'warning',
    partially_refunded: 'warning',
    unpaid: 'default',
    failed: 'error'
  };
  return map[s] || 'default';
}

function timelineType(s: string): any {
  const map: Record<string, any> = {
    pending: 'default',
    paid: 'success',
    confirmed: 'info',
    shipped: 'info',
    delivered: 'success',
    cancelled: 'default',
    refunded: 'error'
  };
  return map[s] || 'default';
}

function numberedShipments(shipments: any[]): { s: any; i: number; no: number }[] {
  return (shipments || []).map((s, i) => ({ s, i, no: i + 1 }));
}

/* ===== 售后记录（RMA 交叉引用） ===== */
const RETURN_STATUS_LABELS: Record<string, string> = {
  requested: '待审核',
  approved: '待收货',
  received: '待退款',
  refunded: '已退款',
  rejected: '已驳回',
  cancelled: '已撤销',
  closed: '已关闭'
};
const RETURN_STATUS_TYPES: Record<string, any> = {
  requested: 'warning',
  approved: 'info',
  received: 'info',
  refunded: 'success',
  rejected: 'error',
  cancelled: 'default',
  closed: 'default'
};
const returnColumns: DataTableColumns<any> = [
  { title: t('page.returns.returnNumber'), key: 'return_number', width: 160 },
  {
    title: t('page.returns.status'),
    key: 'status',
    width: 110,
    render: row =>
      h(
        NTag,
        { size: 'small', type: RETURN_STATUS_TYPES[row.status] || 'default' },
        { default: () => RETURN_STATUS_LABELS[row.status] || row.status }
      )
  },
  { title: t('page.returns.refundAmount'), key: 'refund_amount', width: 120, render: row => money(row.refund_amount) },
  { title: t('page.returns.reason'), key: 'reason', render: row => returnReasonLabel(row.reason, t) },
  { title: t('page.returns.requestedAt'), key: 'requested_at', width: 170, render: row => fmtTime(row.requested_at) }
];

/** 跳转售后管理并按本订单号过滤 */
function goReturns() {
  if (order.value?.order_number) router.push({ path: '/returns', query: { keyword: order.value.order_number } });
}

const itemColumns: DataTableColumns<any> = [
  {
    title: t('page.ordersDetail.productId'),
    key: 'product_id',
    render: row => (row.product_id || '').slice(0, 8) + '...'
  },
  { title: t('common.name'), key: 'name' },
  { title: t('common.sku'), key: 'sku' },
  { title: t('page.products.price'), key: 'price', render: row => `$${row.price}` },
  { title: t('common.quantity'), key: 'quantity' },
  {
    title: t('page.ordersDetail.subtotal'),
    key: 'subtotal',
    render: row => money((row.price || 0) * (row.quantity || 0))
  },
  {
    title: '履约方式',
    key: 'fulfillment_mode',
    render: row => (row.fulfillment_mode === 'dropship' ? '一件代发' : '自采购')
  },
  {
    title: '供应商',
    key: 'supplier_id',
    render: row => (row.fulfillment_mode === 'dropship' ? row.supplier_sku || row.supplier_id || '-' : '-')
  },
  {
    title: '已退/可退',
    key: 'refunded_quantity',
    render: row => `${row.refunded_quantity || 0} / ${row.refundable_quantity ?? row.quantity}`
  },
  {
    title: '采购状态',
    key: 'procurement_status',
    render: row => {
      if (row.fulfillment_mode !== 'dropship') return '-';
      const map: Record<string, { label: string; type: any }> = {
        received: { label: '已入库', type: 'success' },
        requested: { label: '采购中', type: 'warning' }
      };
      const meta = map[row.procurement_status] || { label: '未采购', type: 'default' };
      return h(NTag, { size: 'small', type: meta.type }, { default: () => meta.label });
    }
  },
  {
    title: '采购操作',
    key: 'procurement_action',
    render: row => {
      if (row.fulfillment_mode !== 'dropship') return '-';
      if (row.procurement_status === 'received') {
        return h('span', { class: 'text-[var(--n-text-color-3)]' }, '已完成');
      }
      if (row.procurement_status === 'requested') {
        return h(
          NButton,
          { size: 'tiny', secondary: true, onClick: () => doReceiveProcurement(row) },
          { default: () => '确认到货' }
        );
      }
      return h(
        NButton,
        { size: 'tiny', secondary: true, type: 'primary', onClick: () => openProcure(row) },
        { default: () => '推送采购' }
      );
    }
  }
];

function openReview(approve: boolean) {
  reviewApprove.value = approve;
  reviewReason.value = '';
  reviewBy.value = '';
  actionError.value = '';
  showReview.value = true;
}
function openProcure(row?: any) {
  const pending = dropshipRows().filter((i: any) => i.procurement_status !== 'received');
  procureTargets.value = row ? [row] : pending;
  if (!procureTargets.value.length) {
    actionError.value = '当前没有可推送采购的代发行';
    return;
  }
  procureSupplierId.value = row?.supplier_id || procureTargets.value[0]?.supplier_id || '';
  procureSku.value = row?.supplier_sku || '';
  procureCost.value = Number(row?.procurement_cost || 0);
  actionError.value = '';
  showProcure.value = true;
}
function openShip() {
  shipPackages.value = [{ carrier: '', tracking_number: '', supplier_id: '' }];
  actionError.value = '';
  showShip.value = true;
}

function addShipPackage() {
  shipPackages.value.push({ carrier: '', tracking_number: '', supplier_id: '' });
}

function removeShipPackage(index: number) {
  shipPackages.value.splice(index, 1);
}
function openRefund(row?: any) {
  const rows: any[] = row ? [row] : order.value?.items || [];
  refundLines.value = rows
    .map(i => ({
      id: i.id,
      name: i.name,
      quantity: Number(i.refundable_quantity ?? i.quantity) || 0,
      refundable: Number(i.refundable_quantity ?? i.quantity) || 0
    }))
    .filter(line => line.refundable > 0);
  if (!refundLines.value.length) {
    actionError.value = '当前没有可退数量的商品行';
    return;
  }
  refundReason.value = ORDER_REFUND_REASON_DEFAULT;
  refundShipping.value = false;
  refundRestock.value = false;
  refundIdempotencyKey.value = newRefundIdempotencyKey();
  actionError.value = '';
  showRefund.value = true;
}

function openCancel() {
  cancelReason.value = ORDER_CANCEL_REASON_DEFAULT;
  cancelRefund.value = hasRefundableBalance();
  actionError.value = '';
  showCancel.value = true;
}

async function doReview() {
  actionLoading.value = true;
  actionError.value = '';
  try {
    if (!reviewApprove.value && !reviewReason.value.trim()) {
      actionError.value = t('page.ordersDetail.rejectReasonRequired');
      return;
    }
    // 拒绝 = 取消 + 默认全额退款：refund 不传，由后端按可退余额自动判定
    await post(`/api/admin/v1/orders/${route.params.id}/review`, {
      approved: reviewApprove.value,
      reason: reviewReason.value,
      reviewed_by: reviewBy.value
    });
    showReview.value = false;
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || t('page.ordersDetail.reviewFailed');
  } finally {
    actionLoading.value = false;
  }
}

async function doProcure() {
  actionLoading.value = true;
  actionError.value = '';
  try {
    await post(`/api/admin/v1/orders/${route.params.id}/procure`, {
      items: procureTargets.value.map((i: any) => ({
        order_item_id: i.id,
        supplier_id: procureSupplierId.value || null,
        supplier_sku: procureSku.value || null,
        cost: Number(procureCost.value) || null
      }))
    });
    showProcure.value = false;
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || t('page.ordersDetail.procurementFailed');
  } finally {
    actionLoading.value = false;
  }
}

async function doReceiveProcurement(row?: any) {
  actionLoading.value = true;
  actionError.value = '';
  try {
    const ids = row
      ? [row.id]
      : dropshipRows()
          .filter((i: any) => i.procurement_status === 'requested')
          .map((i: any) => i.id);
    await post(`/api/admin/v1/orders/${route.params.id}/procure/receive`, { order_item_ids: ids });
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || t('page.ordersDetail.procurementFailed');
  } finally {
    actionLoading.value = false;
  }
}

async function doShip() {
  actionLoading.value = true;
  actionError.value = '';
  try {
    const packages = shipPackages.value
      .map(pkg => ({
        carrier: pkg.carrier.trim(),
        tracking_number: pkg.tracking_number.trim(),
        supplier_id: (pkg.supplier_id || '').trim() || null
      }))
      .filter(pkg => pkg.tracking_number && pkg.carrier);
    if (!packages.length) {
      actionError.value = t('page.ordersDetail.shipRequirePackage');
      return;
    }
    await post(`/api/admin/v1/orders/${route.params.id}/ship`, { packages });
    showShip.value = false;
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || t('page.ordersDetail.shipFailed');
  } finally {
    actionLoading.value = false;
  }
}

async function doRefund() {
  actionLoading.value = true;
  actionError.value = '';
  try {
    const items = refundLines.value
      .filter(line => Number(line.quantity) > 0)
      .map(line => ({ order_item_id: line.id, quantity: Number(line.quantity) }));
    if (!items.length) {
      actionError.value = '请填写退款数量';
      return;
    }
    await post(`/api/admin/v1/orders/${route.params.id}/refund`, {
      reason: refundReason.value,
      items,
      refund_shipping: refundShipping.value,
      restock: refundRestock.value,
      // 幂等键随弹窗生成：重复提交/网络重试不会二次扣款
      idempotency_key: refundIdempotencyKey.value || undefined
    });
    showRefund.value = false;
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || t('page.ordersDetail.refundFailed');
  } finally {
    actionLoading.value = false;
  }
}

async function doCancel() {
  actionLoading.value = true;
  actionError.value = '';
  try {
    await post(`/api/admin/v1/orders/${route.params.id}/cancel`, {
      reason: cancelReason.value,
      // 取消的退款勾选按「是否有可退余额」判定，与仅退款入口的阶段化显隐策略解耦
      refund: hasRefundableBalance() && cancelRefund.value
    });
    showCancel.value = false;
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || '取消失败';
  } finally {
    actionLoading.value = false;
  }
}

async function loadOrder() {
  try {
    const res = await get(`/api/admin/v1/orders/${route.params.id}`);
    order.value = res.data;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

onMounted(loadOrder);
</script>

<template>
  <div class="flex flex-col gap-4">
    <NSpin :show="loading">
      <template v-if="order">
        <div class="flex items-center gap-2 mb-4">
          <NButton @click="$router.push('/orders')">{{ $t('common.backToList') }}</NButton>
        </div>

        <NSpace class="mb-4 flex-wrap">
          <NButton v-if="order.status === 'confirmed'" type="success" @click="openReview(true)">
            {{ $t('page.ordersDetail.approve') }}
          </NButton>
          <NButton v-if="order.status === 'confirmed'" type="error" @click="openReview(false)">
            {{ $t('page.ordersDetail.reject') }}
          </NButton>
          <NButton v-if="canShip()" type="primary" @click="openShip()">
            {{ $t('page.ordersDetail.ship') }}
          </NButton>
          <NButton v-if="canRefund()" type="error" @click="openRefund()">
            {{ $t('page.ordersDetail.refundOnly') }}
          </NButton>
          <NButton v-if="canCancel()" @click="openCancel()">取消订单</NButton>
        </NSpace>

        <div v-if="shipBlocked()" class="mb-4 text-sm text-red-500">
          {{ $t('page.ordersDetail.shipBlockedByReview') }}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Order Info -->
          <NCard :title="$t('page.ordersDetail.orderInfo')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.orders.orderNumber') }}</span>
                {{ order.order_number }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('common.userId') }}</span>
                {{ order.user_id }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('common.status') }}</span>
                <NTag :type="statusType(order.status)" size="small">{{ statusLabel(order.status) }}</NTag>
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.settings.defaultCurrency') }}</span>
                {{ order.currency }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('common.created') }}</span>
                {{ order.created_at }}
              </div>
            </div>
          </NCard>

          <!-- Payment Info -->
          <NCard :title="$t('page.ordersDetail.paymentInfo')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.paymentMethod') }}</span>
                {{ order.payment_method || '-' }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.paymentStatus') }}</span>
                <NTag :type="paymentStatusType(order.payment_status)" size="small">
                  {{ paymentLabel(order.payment_status) }}
                </NTag>
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">已退款金额</span>
                {{ money(order.refunded_amount || 0) }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">可退款金额</span>
                {{ money(order.refundable_amount || 0) }}
              </div>
              <div v-if="order.payment_intent_id">
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.paymentIntentId') }}</span>
                {{ order.payment_intent_id }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.paidAt') }}</span>
                {{ order.paid_at ? fmtTime(order.paid_at) : $t('page.ordersDetail.notPaid') }}
              </div>
            </div>
          </NCard>

          <!-- Shipping -->
          <NCard v-if="order.shipping_address" :title="$t('page.ordersDetail.shippingAddress')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('common.name') }}</span>
                {{ order.shipping_address.name }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.addressLine1') }}</span>
                {{ order.shipping_address.line1 }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.city') }}</span>
                {{ order.shipping_address.city }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.state') }}</span>
                {{ order.shipping_address.state }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.country') }}</span>
                {{ order.shipping_address.country }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.phone') }}</span>
                {{ order.shipping_address.phone }}
              </div>
            </div>
          </NCard>

          <!-- Amount Details -->
          <NCard :title="$t('page.ordersDetail.amountDetails')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.subtotal') }}</span>
                {{ money(order.subtotal) }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.tax') }}</span>
                {{ money(order.tax) }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.shippingCost') }}</span>
                {{ money(order.shipping_cost) }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.discount') }}</span>
                -{{ money(order.discount) }}
              </div>
              <div class="border-t pt-2 font-semibold">
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.orders.total') }}</span>
                {{ money(order.total) }}
              </div>
            </div>
          </NCard>

          <!-- Order Items -->
          <NCard :title="$t('page.ordersDetail.orderItems')" size="small" class="md:col-span-2">
            <NDataTable :columns="itemColumns" :data="order.items || []" :bordered="true" size="small" />
          </NCard>

          <!-- Review -->
          <NCard v-if="order.review_status" :title="$t('page.ordersDetail.reviewStatus')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.reviewedBy') }}</span>
                {{ order.review_status.reviewed_by }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.approved') }}</span>
                {{ order.review_status.approved }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.reason') }}</span>
                {{ order.review_status.reason || '-' }}
              </div>
            </div>
          </NCard>

          <!-- Procurement（行级采购单） -->
          <NCard v-if="dropshipRows().length" :title="$t('page.ordersDetail.procurementInfo')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">采购汇总</span>
                采购中 {{ order.procurement_summary?.requested || 0 }} / 已入库
                {{ order.procurement_summary?.received || 0 }} / 未采购
                {{ order.procurement_summary?.pending || 0 }}
              </div>
              <div v-for="row in dropshipRows()" :key="row.id" class="border-t pt-2 flex flex-col gap-1">
                <div class="font-medium">{{ row.name }}（SKU: {{ row.sku || '-' }}）</div>
                <div>
                  <span class="text-[var(--n-text-color-3)]">采购状态</span>
                  {{ procurementStatusLabel(row.procurement_status) }}
                </div>
                <div v-if="row.supplier_id">
                  <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.supplier') }}</span>
                  {{ row.supplier_id }}
                </div>
                <div v-if="row.supplier_sku">
                  <span class="text-[var(--n-text-color-3)]">{{ $t('common.sku') }}</span>
                  {{ row.supplier_sku }}
                </div>
                <div v-if="row.procurement_cost != null">
                  <span class="text-[var(--n-text-color-3)]">{{ $t('common.cost') }}</span>
                  ${{ row.procurement_cost }}
                </div>
              </div>
              <NButton
                v-if="order.procurement_summary?.requested"
                size="tiny"
                secondary
                @click="doReceiveProcurement()"
              >
                全部确认到货
              </NButton>
            </div>
          </NCard>

          <!-- After-sales (RMA) -->
          <NCard :title="$t('page.ordersDetail.afterSalesRecords')" size="small" class="md:col-span-2">
            <template v-if="order.return_requests && order.return_requests.length">
              <NDataTable :columns="returnColumns" :data="order.return_requests" :bordered="false" size="small" />
              <div class="mt-3">
                <NButton size="small" secondary type="primary" @click="goReturns()">
                  {{ $t('page.ordersDetail.viewInReturns') }}
                </NButton>
              </div>
            </template>
            <NEmpty v-else :description="$t('page.ordersDetail.noAfterSales')" />
          </NCard>

          <!-- Shipments -->
          <NCard
            v-if="(order.shipments && order.shipments.length) || order.tracking_number"
            :title="$t('page.ordersDetail.shipments')"
            size="small"
            class="md:col-span-2"
          >
            <template v-if="order.shipments && order.shipments.length">
              <div
                v-for="entry in numberedShipments(order.shipments)"
                :key="entry.s.id || entry.i"
                class="border rounded p-3 mb-2 flex flex-col gap-2 text-sm"
              >
                <div class="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span class="font-medium">#{{ entry.no }}</span>
                  <span>
                    <span class="text-[var(--n-text-color-3)]">{{ $t('page.shipments.carrier') }}</span>
                    {{ entry.s.carrier || '-' }}
                  </span>
                  <span>
                    <span class="text-[var(--n-text-color-3)]">{{ $t('page.shipments.trackingNumber') }}</span>
                    {{ entry.s.tracking_number || '-' }}
                  </span>
                  <span v-if="entry.s.tracking_url">
                    <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.trackingUrl') }}</span>
                    <a :href="entry.s.tracking_url" target="_blank" rel="noopener noreferrer" class="text-blue-500">
                      {{ entry.s.tracking_url }}
                    </a>
                  </span>
                  <NTag :type="statusType(entry.s.status)" size="small">{{ statusLabel(entry.s.status) }}</NTag>
                </div>
                <div v-if="entry.s.origin || entry.s.destination" class="text-[var(--n-text-color-3)]">
                  {{ entry.s.origin || 'N/A' }} → {{ entry.s.destination || 'N/A' }}
                </div>
                <div v-if="entry.s.events && entry.s.events.length">
                  <div class="text-[var(--n-text-color-3)] mb-1">{{ $t('page.ordersDetail.shipmentEvents') }}</div>
                  <div class="flex flex-col gap-1">
                    <div v-for="(ev, eidx) in entry.s.events" :key="eidx" class="text-xs">
                      <span class="text-[var(--n-text-color-3)]">{{ fmtTime(ev.time) }}</span>
                      <span class="ml-2">{{ ev.label || ev.status || '-' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="text-sm">
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.shipments.trackingNumber') }}</span>
                {{ order.tracking_number || '-' }}
              </div>
            </template>
          </NCard>

          <!-- Timeline -->
          <NCard :title="$t('page.ordersDetail.timeline')" size="small" class="md:col-span-2">
            <NTimeline v-if="order.timeline && order.timeline.length">
              <NTimelineItem
                v-for="(ev, idx) in order.timeline"
                :key="idx"
                :type="timelineType(ev.status)"
                :time="ev.time ? fmtTime(ev.time) : ''"
              >
                <span class="text-sm">{{ t(`page.ordersDetail.event_${ev.status}`) || ev.status }}</span>
              </NTimelineItem>
            </NTimeline>
            <NEmpty v-else :description="$t('common.noData')" />
          </NCard>
        </div>
      </template>
      <template v-else-if="!loading">
        <NEmpty :description="$t('common.noData')" />
      </template>
    </NSpin>

    <!-- Review Modal -->
    <NModal v-model:show="showReview" preset="card" :title="$t('page.ordersDetail.approveOrder')" style="width: 440px">
      <div class="flex flex-col gap-3">
        <NFormItem :label="reviewApprove ? $t('page.ordersDetail.reason') : $t('page.ordersDetail.reason') + ' *'">
          <NSelect
            v-model:value="reviewReason"
            :options="rejectReasonOptions"
            filterable
            tag
            clearable
            :placeholder="$t('page.ordersDetail.reasonPlaceholder')"
          />
        </NFormItem>
        <NFormItem :label="$t('page.ordersDetail.reviewedBy')"><NInput v-model:value="reviewBy" /></NFormItem>
        <div v-if="!reviewApprove" class="text-sm text-[var(--n-text-color-3)]">
          {{
            hasRefundableBalance()
              ? $t('page.ordersDetail.rejectRefundHint', { amount: money(refundableAmount()) })
              : $t('page.ordersDetail.rejectNoRefundHint')
          }}
        </div>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showReview = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="actionLoading" @click="doReview">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Procure Modal（行级推送） -->
    <NModal
      v-model:show="showProcure"
      preset="card"
      :title="$t('page.ordersDetail.pushToProcurement')"
      style="width: 440px"
    >
      <div class="flex flex-col gap-3">
        <div class="text-sm">
          <div>目标商品行（{{ procureTargets.length }}）</div>
          <div v-for="row in procureTargets" :key="row.id" class="text-[var(--n-text-color-3)]">
            {{ row.name }} × {{ row.quantity }}
          </div>
        </div>
        <NFormItem :label="$t('page.ordersDetail.supplierId')" required>
          <NInput v-model:value="procureSupplierId" />
        </NFormItem>
        <NFormItem :label="$t('page.ordersDetail.supplierSku')"><NInput v-model:value="procureSku" /></NFormItem>
        <NFormItem :label="$t('common.cost')">
          <NInputNumber v-model:value="procureCost" :min="0" :step="0.01" style="width: 100%" />
        </NFormItem>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showProcure = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="actionLoading" @click="doProcure">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Ship Modal -->
    <NModal v-model:show="showShip" preset="card" :title="$t('page.ordersDetail.shipOrder')" style="width: 520px">
      <div class="flex flex-col gap-3">
        <div
          v-for="(pkg, index) in shipPackages"
          :key="index"
          class="border border-dashed rounded p-3 flex flex-col gap-2"
        >
          <div class="flex items-center justify-between text-xs text-[var(--n-text-color-3)]">
            <span>{{ $t('page.ordersDetail.packageNo', { no: index + 1 }) }}</span>
            <NButton
              v-if="shipPackages.length > 1"
              size="tiny"
              quaternary
              type="error"
              @click="removeShipPackage(index)"
            >
              {{ $t('page.ordersDetail.removePackage') }}
            </NButton>
          </div>
          <NFormItem :label="$t('page.shipments.trackingNumber')" required :show-feedback="false">
            <NInput v-model:value="pkg.tracking_number" :placeholder="$t('page.ordersDetail.trackingPlaceholder')" />
          </NFormItem>
          <NFormItem :label="$t('page.shipments.carrier')" :show-feedback="false">
            <NInput v-model:value="pkg.carrier" placeholder="DHL / UPS / FedEx / SF" />
          </NFormItem>
          <NFormItem label="供应商 ID（代发包裹选填）" :show-feedback="false">
            <NInput v-model:value="pkg.supplier_id" placeholder="留空表示自发货包裹" />
          </NFormItem>
        </div>
        <NButton size="small" dashed block @click="addShipPackage">
          {{ $t('page.ordersDetail.addPackage') }}
        </NButton>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showShip = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="actionLoading" @click="doShip">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Refund Modal（行级部分退款） -->
    <NModal v-model:show="showRefund" preset="card" :title="$t('page.ordersDetail.refundOrder')" style="width: 560px">
      <div class="flex flex-col gap-3">
        <div v-for="line in refundLines" :key="line.id" class="border rounded p-3 flex flex-col gap-2 text-sm">
          <div class="font-medium">{{ line.name }}</div>
          <div class="text-[var(--n-text-color-3)]">可退数量 {{ line.refundable }}</div>
          <NFormItem label="退款数量" :show-feedback="false">
            <NInputNumber v-model:value="line.quantity" :min="0" :max="line.refundable" style="width: 100%" />
          </NFormItem>
        </div>
        <NCheckbox v-model:checked="refundShipping">同时退还运费</NCheckbox>
        <NCheckbox v-model:checked="refundRestock">退回商品并回补库存</NCheckbox>
        <NFormItem :label="$t('page.ordersDetail.reason')">
          <NSelect
            v-model:value="refundReason"
            :options="refundReasonOptions"
            filterable
            tag
            clearable
            :placeholder="$t('page.ordersDetail.reasonPlaceholder')"
          />
        </NFormItem>
        <div class="text-sm text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.refundOnlyHint') }}</div>
        <div class="text-sm text-[var(--n-text-color-3)]">本次可退余额 {{ money(refundableAmount()) }}</div>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showRefund = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="error" :loading="actionLoading" @click="doRefund">
            {{ $t('page.ordersDetail.confirmRefund') }}
          </NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Cancel Modal（取消即退款的复合入口） -->
    <NModal v-model:show="showCancel" preset="card" title="取消订单" style="width: 440px">
      <div class="flex flex-col gap-3">
        <div class="text-sm text-[var(--n-text-color-3)]">取消将终止订单履约（回补自采购库存），可按需一并退款。</div>
        <NFormItem :label="$t('page.ordersDetail.reason')">
          <NSelect
            v-model:value="cancelReason"
            :options="cancelReasonOptions"
            filterable
            tag
            clearable
            :placeholder="$t('page.ordersDetail.reasonPlaceholder')"
          />
        </NFormItem>
        <NCheckbox v-if="hasRefundableBalance()" v-model:checked="cancelRefund">
          同时全额退款（当前可退 {{ money(refundableAmount()) }}）
        </NCheckbox>
        <div v-else class="text-sm text-[var(--n-text-color-3)]">
          {{ $t('page.ordersDetail.cancelNoRefundHint') }}
        </div>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCancel = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="error" :loading="actionLoading" @click="doCancel">确认取消</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
