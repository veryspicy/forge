<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSpace,
  NSpin,
  NTag
} from 'naive-ui';
import { useI18n } from 'vue-i18n';
import { get, post } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const route = useRoute();
const { t } = useI18n();
const order = ref<any>(null);
const loading = ref(true);

const showReview = ref(false);
const reviewApprove = ref(true);
const reviewReason = ref('');
const reviewBy = ref('');
const showProcure = ref(false);
const procureSupplierId = ref('');
const procureSku = ref('');
const procureCost = ref(0);
const showShip = ref(false);
const shipTracking = ref('');
const shipCarrier = ref('');
const showRefund = ref(false);
const refundReason = ref('');
const actionError = ref('');
const actionLoading = ref(false);

const REFUNDABLE_STATUSES = ['confirmed', 'processing', 'procuring', 'procure_failed'];

function isRefundable(s: string): boolean {
  return REFUNDABLE_STATUSES.includes(s);
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
  }
];

function openReview(approve: boolean) {
  reviewApprove.value = approve;
  reviewReason.value = '';
  reviewBy.value = '';
  actionError.value = '';
  showReview.value = true;
}
function openProcure() {
  procureSupplierId.value = order.value?.procurement_info?.supplier_id || '';
  procureSku.value = order.value?.procurement_info?.supplier_sku || '';
  procureCost.value = order.value?.procurement_info?.cost || 0;
  actionError.value = '';
  showProcure.value = true;
}
function openShip() {
  shipTracking.value = '';
  shipCarrier.value = '';
  actionError.value = '';
  showShip.value = true;
}
function openRefund() {
  refundReason.value = '';
  actionError.value = '';
  showRefund.value = true;
}

async function doReview() {
  actionLoading.value = true;
  actionError.value = '';
  try {
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
      supplier_id: procureSupplierId.value,
      supplier_sku: procureSku.value,
      cost: procureCost.value
    });
    showProcure.value = false;
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
    await post(`/api/admin/v1/orders/${route.params.id}/ship`, {
      tracking_number: shipTracking.value,
      carrier: shipCarrier.value
    });
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
    await post(`/api/admin/v1/orders/${route.params.id}/refund`, { reason: refundReason.value });
    showRefund.value = false;
    await loadOrder();
  } catch (e: any) {
    actionError.value = e.response?.data?.detail || t('page.ordersDetail.refundFailed');
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
          <NButton v-if="order.status === 'processing'" type="primary" @click="openProcure()">
            {{ $t('page.ordersDetail.pushToProcurement') }}
          </NButton>
          <NButton v-if="order.status === 'procure_failed'" type="error" @click="openProcure()">
            {{ $t('page.ordersDetail.retryProcurement') }}
          </NButton>
          <NButton v-if="isRefundable(order.status)" type="error" @click="openRefund()">
            {{ $t('page.ordersDetail.refund') }}
          </NButton>
          <NButton v-if="order.status === 'procuring'" type="primary" @click="openShip()">
            {{ $t('page.ordersDetail.ship') }}
          </NButton>
        </NSpace>

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
                <NTag :type="statusType(order.status)" size="small">{{ order.status }}</NTag>
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
                  {{ order.payment_status || '-' }}
                </NTag>
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

          <!-- Procurement -->
          <NCard v-if="order.procurement_info" :title="$t('page.ordersDetail.procurementInfo')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.ordersDetail.supplier') }}</span>
                {{ order.procurement_info.supplier_id }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('common.sku') }}</span>
                {{ order.procurement_info.supplier_sku }}
              </div>
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('common.cost') }}</span>
                ${{ order.procurement_info.cost }}
              </div>
            </div>
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
                  <NTag :type="statusType(entry.s.status)" size="small">{{ entry.s.status || '-' }}</NTag>
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
        <NFormItem :label="$t('page.ordersDetail.reason')">
          <NInput v-model:value="reviewReason" type="textarea" :rows="2" />
        </NFormItem>
        <NFormItem :label="$t('page.ordersDetail.reviewedBy')"><NInput v-model:value="reviewBy" /></NFormItem>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showReview = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="actionLoading" @click="doReview">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Procure Modal -->
    <NModal
      v-model:show="showProcure"
      preset="card"
      :title="$t('page.ordersDetail.pushToProcurement')"
      style="width: 440px"
    >
      <div class="flex flex-col gap-3">
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
    <NModal v-model:show="showShip" preset="card" :title="$t('page.ordersDetail.shipOrder')" style="width: 440px">
      <div class="flex flex-col gap-3">
        <NFormItem :label="$t('page.shipments.trackingNumber')" required>
          <NInput v-model:value="shipTracking" />
        </NFormItem>
        <NFormItem :label="$t('page.shipments.carrier')"><NInput v-model:value="shipCarrier" /></NFormItem>
        <div v-if="actionError" class="text-red-500 text-sm">{{ actionError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showShip = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="actionLoading" @click="doShip">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Refund Modal -->
    <NModal v-model:show="showRefund" preset="card" :title="$t('page.ordersDetail.refundOrder')" style="width: 440px">
      <div class="flex flex-col gap-3">
        <NFormItem :label="$t('page.ordersDetail.reason')">
          <NInput v-model:value="refundReason" type="textarea" :rows="2" />
        </NFormItem>
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
  </div>
</template>
