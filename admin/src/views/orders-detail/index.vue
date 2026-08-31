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

function statusType(s: string): any {
  const map: Record<string, any> = {
    PAID: 'info',
    PROCESSING: 'warning',
    PROCURING: 'warning',
    PROCURE_FAILED: 'error',
    SHIPPED: 'info',
    DELIVERED: 'success',
    CANCELLED: 'default',
    REFUNDED: 'error'
  };
  return map[s] || 'default';
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
  { title: t('page.ordersDetail.subtotal'), key: 'subtotal', render: row => `$${row.subtotal}` }
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
          <NButton v-if="order.status === 'PAID'" type="success" @click="openReview(true)">
            {{ $t('page.ordersDetail.approve') }}
          </NButton>
          <NButton v-if="order.status === 'PAID'" type="error" @click="openReview(false)">
            {{ $t('page.ordersDetail.reject') }}
          </NButton>
          <NButton v-if="order.status === 'PROCESSING'" type="primary" @click="openProcure()">
            {{ $t('page.ordersDetail.pushToProcurement') }}
          </NButton>
          <NButton v-if="order.status === 'PROCURE_FAILED'" type="error" @click="openProcure()">
            {{ $t('page.ordersDetail.retryProcurement') }}
          </NButton>
          <NButton @click="openRefund()">{{ $t('page.ordersDetail.refund') }}</NButton>
          <NButton v-if="order.status === 'PROCURING'" type="primary" @click="openShip()">
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
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.orders.total') }}</span>
                ${{ order.total }}
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

          <!-- Tracking -->
          <NCard v-if="order.tracking_number" :title="$t('page.ordersDetail.shipping')" size="small">
            <div class="flex flex-col gap-2 text-sm">
              <div>
                <span class="text-[var(--n-text-color-3)]">{{ $t('page.shipments.trackingNumber') }}</span>
                {{ order.tracking_number }}
              </div>
            </div>
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
