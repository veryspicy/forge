<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">{{ $t('orders.title') }}</h1>

    <!-- Tabs -->
    <div class="flex gap-2 mb-6 overflow-x-auto pb-2">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="px-4 py-2 rounded-full text-sm font-medium transition whitespace-nowrap"
        :class="
          activeTab === tab.key
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        "
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Orders List -->
    <div v-if="filteredOrders.length > 0" class="space-y-4">
      <div
        v-for="order in filteredOrders"
        :key="order.id"
        class="bg-white rounded-xl shadow-sm border overflow-hidden"
      >
        <!-- Header: order info + status on top -->
        <div class="flex items-center justify-between gap-4 px-6 pt-5 pb-3">
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900 truncate">#{{ order.order_number || order.id }}</p>
            <p class="text-xs text-gray-500 mt-0.5">{{ $t('orders.date') }}: {{ formatDate(order.created_at) }}</p>
          </div>
          <OrderStatusBadge :status="order.status" />
        </div>

        <!-- Items -->
        <div class="px-6 py-2 border-t space-y-3">
          <div
            v-for="item in order.items"
            :key="item.id"
            class="flex items-center gap-4"
          >
            <div class="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400 text-xs flex-shrink-0">
              <img
                v-if="item.image"
                :src="item.image"
                :alt="item.name"
                class="w-full h-full object-cover rounded-lg"
              >
              <span v-else>{{ $t('orders.noImage') }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ item.name }}</p>
              <p class="text-xs text-gray-500">{{ $t('orders.qty') }}: {{ item.quantity }}</p>
            </div>
            <p class="text-sm font-medium text-gray-900">{{ formatPrice(item.price) }}</p>
          </div>
        </div>

        <!-- Footer: total left + actions bottom-right -->
        <div class="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-t bg-gray-50/60">
          <p class="font-semibold text-gray-900">{{ $t('orders.total') }}: {{ formatPrice(order.total) }}</p>
          <div class="flex items-center gap-2 flex-wrap">
            <button
              v-if="canDelete(order.status)"
              class="px-4 py-2 text-sm border border-gray-200 text-gray-500 rounded-lg hover:text-red-600 hover:border-red-200 transition font-medium disabled:opacity-50"
              :disabled="busyId === (order.order_number || order.id)"
              @click="deleteOrder(order.order_number || order.id)"
            >
              {{ busyId === (order.order_number || order.id) ? $t('orders.deleting') : $t('orders.deleteOrder') }}
            </button>
            <button
              class="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:border-primary-300 hover:text-primary-700 transition font-medium"
              @click="viewOrder(order.order_number || order.id)"
            >
              {{ $t('orders.viewDetails') }}
            </button>
            <button
              v-if="canCancel(order.status)"
              class="px-4 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition font-medium disabled:opacity-50"
              :disabled="busyId === (order.order_number || order.id)"
              @click="cancelOrder(order.order_number || order.id)"
            >
              {{ busyId === (order.order_number || order.id) ? $t('orders.cancelling') : $t('orders.cancelOrder') }}
            </button>
            <button
              v-if="canEdit(order.status)"
              class="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:border-primary-300 hover:text-primary-700 transition font-medium"
              @click="openEditModal(order)"
            >
              {{ $t('orders.editOrder') }}
            </button>
            <button
              v-if="canPay(order)"
              class="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium"
              @click="goPay(order.order_number || order.id)"
            >
              {{ $t('orders.pay') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-16">
      <div class="text-5xl mb-4">📦</div>
      <h3 class="text-xl font-semibold text-gray-900 mb-2">{{ $t('orders.noOrders') }}</h3>
      <p class="text-gray-500 mb-6">{{ $t('orders.noOrdersHint') }}</p>
      <NuxtLink
        :to="localePath('/products')"
        class="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium"
      >
        {{ $t('orders.startShopping') }}
      </NuxtLink>
    </div>

    <!-- Edit Shipping Address Modal -->
    <div v-if="showEditModal" class="fixed inset-0 z-50 overflow-y-auto" aria-modal="true">
      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="closeEditModal"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-2xl shadow-2xl ring-1 ring-white/60 max-w-lg w-full text-left">
          <div class="px-6 pt-5 pb-4 border-b">
            <h3 class="text-lg font-semibold text-gray-900">{{ $t('orders.editShippingAddress') }}</h3>
            <p class="text-sm text-gray-500 mt-1">{{ $t('orders.editShippingAddressHint') }}</p>
          </div>
          <div class="px-6 py-4 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.firstName') }}</label>
                <input
                  v-model.trim="editForm.firstName"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.lastName') }}</label>
                <input
                  v-model.trim="editForm.lastName"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                >
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.address') }}</label>
              <input
                v-model.trim="editForm.address"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              >
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.city') }}</label>
                <input
                  v-model.trim="editForm.city"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.zipCode') }}</label>
                <input
                  v-model.trim="editForm.zipCode"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                >
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.country') }}</label>
              <select
                v-model="editForm.country"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="US">United States</option>
                <option value="UK">United Kingdom</option>
                <option value="DE">Germany</option>
                <option value="FR">France</option>
              </select>
            </div>
          </div>
          <div class="px-6 py-4 border-t flex justify-end gap-3">
            <button
              class="px-4 py-2 text-sm border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition font-medium"
              @click="closeEditModal"
            >
              {{ $t('common.cancel') }}
            </button>
            <button
              class="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="savingEdit || !canSubmitEdit"
              @click="saveEditAddress"
            >
              {{ savingEdit ? $t('orders.savingAddress') : $t('orders.saveAddress') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOrderStore } from '~/stores/order'
import { useCurrency } from '~/composables/useCurrency'
const localePath = useLocalePath()

definePageMeta({
  middleware: 'auth',
})

const orderStore = useOrderStore()
const { t } = useI18n()
const { formatPrice } = useCurrency()

const activeTab = ref('all')

const tabs = computed(() => [
  { key: 'all', label: t('orders.all') },
  { key: 'pending', label: t('orders.pending') },
  { key: 'confirmed', label: t('orders.confirmed') },
  { key: 'shipped', label: t('orders.shipped') },
  { key: 'delivered', label: t('orders.delivered') },
  { key: 'cancelled', label: t('orders.cancelled') },
])

const filteredOrders = computed(() => {
  if (activeTab.value === 'all') return orderStore.orders
  return orderStore.orders.filter((o: any) => o.status === activeTab.value)
})

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString()
}

function viewOrder(orderNo: string | number) {
  navigateTo(`/orders/${orderNo}`)
}

const busyId = ref<string | null>(null)
const { toast } = useToast()

// 操作可用性：与后端状态机对齐（未发货阶段 pending/confirmed/processing 可取消/可改地址）
function canCancel(status: string): boolean {
  return status === 'pending' || status === 'confirmed' || status === 'processing'
}

function canEdit(status: string): boolean {
  return status === 'pending' || status === 'confirmed' || status === 'processing'
}

function canPay(order: any): boolean {
  return (
    !order.deleted_at &&
    (order.payment_status === 'unpaid' || (order.status || '').toLowerCase() === 'pending')
  )
}

function canDelete(status: string): boolean {
  return status === 'delivered' || status === 'cancelled'
}

// 去支付：跳转详情页并自动唤起支付弹窗（?pay=1）
function goPay(orderNo: string | number) {
  navigateTo(`/orders/${orderNo}?pay=1`)
}

async function cancelOrder(orderNo: string | number) {
  const key = String(orderNo)
  if (!confirm(t('orders.cancelConfirmText') as string)) return
  busyId.value = key
  try {
    await orderStore.cancelOrder(key)
    toast.success(t('orders.cancelled'))
  } catch {
    toast.error(t('orders.failedToLoad'))
  } finally {
    busyId.value = null
  }
}

async function deleteOrder(orderNo: string | number) {
  const key = String(orderNo)
  if (!confirm(t('orders.deleteConfirmText') as string)) return
  busyId.value = key
  try {
    await orderStore.deleteOrder(key)
    toast.success(t('orders.orderDeleted'))
  } catch {
    toast.error(t('orders.failedToLoad'))
  } finally {
    busyId.value = null
  }
}

// ---- Edit shipping address modal ----
const showEditModal = ref(false)
const savingEdit = ref(false)
const editingOrderNo = ref<string | null>(null)
const editForm = ref({
  firstName: '',
  lastName: '',
  address: '',
  city: '',
  zipCode: '',
  country: 'US',
})

const canSubmitEdit = computed(() => {
  const f = editForm.value
  return !!(f.firstName && f.lastName && f.address && f.city && f.zipCode && f.country)
})

function openEditModal(order: any) {
  const addr: any = order.shipping_address || {}
  const names = String(addr.name || '').split(' ')
  editForm.value = {
    firstName: names.shift() || '',
    lastName: names.join(' '),
    address: addr.line1 || '',
    city: addr.city || '',
    zipCode: addr.postal_code || '',
    country: addr.country || 'US',
  }
  editingOrderNo.value = String(order.order_number || order.id)
  showEditModal.value = true
}

function closeEditModal() {
  if (savingEdit.value) return
  showEditModal.value = false
  editingOrderNo.value = null
}

async function saveEditAddress() {
  if (!editingOrderNo.value || savingEdit.value) return
  savingEdit.value = true
  try {
    const f = editForm.value
    const payload = {
      name: `${f.firstName} ${f.lastName}`.trim(),
      line1: f.address,
      line2: '',
      city: f.city,
      state: '',
      postal_code: f.zipCode,
      country: f.country,
    }
    await orderStore.updateShippingAddress(editingOrderNo.value, payload)
    toast.success(t('orders.addressUpdated'))
    showEditModal.value = false
    editingOrderNo.value = null
  } catch {
    toast.error(t('orders.addressUpdateFailed'))
  } finally {
    savingEdit.value = false
  }
}

onMounted(() => {
  orderStore.loadOrders()
})
</script>
