<template>
  <div class="min-h-screen bg-gray-50 py-8">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Loading -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>

      <template v-else-if="order">
        <!-- Breadcrumb -->
        <nav class="flex mb-6 text-sm text-gray-500">
          <button @click="navigateTo('/orders')" class="hover:text-gray-700">{{ $t('orders.orders') }}</button>
          <svg class="w-4 h-4 mx-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
          <span class="text-gray-900 font-medium">#{{ order.order_number || order.id }}</span>
        </nav>

        <!-- Order Header -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <div class="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 class="text-2xl font-bold text-gray-900">
                {{ $t('orders.order') }} #{{ order.order_number || order.id }}
              </h1>
              <p class="text-sm text-gray-500 mt-1">
                {{ $t('orders.placedOn') }} {{ formatDate(order.created_at || order.date) }}
              </p>
            </div>
            <div class="flex items-center space-x-3">
              <OrderStatusBadge :status="order.status" size="lg" />
              <button
                v-if="canCancel"
                @click="showCancelModal = true"
                class="px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
              >
                {{ $t('orders.cancelOrder') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Order Progress Timeline -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.tracking') }}</h2>
          <div class="relative">
            <div class="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200"></div>
            <div class="space-y-6">
              <div
                v-for="(step, idx) in orderSteps"
                :key="step.key"
                class="relative flex items-start"
              >
                <div
                  :class="[
                    'relative z-10 flex items-center justify-center w-10 h-10 rounded-full border-2',
                    step.completed
                      ? 'bg-indigo-600 border-indigo-600'
                      : step.active
                      ? 'border-indigo-600 bg-white'
                      : 'border-gray-300 bg-white'
                  ]"
                >
                  <svg
                    v-if="step.completed"
                    class="w-5 h-5 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  <div
                    v-else-if="step.active"
                    class="w-3 h-3 rounded-full bg-indigo-600"
                  ></div>
                  <span v-else class="text-gray-400 text-sm">{{ idx + 1 }}</span>
                </div>
                <div class="ml-4">
                  <p
                    :class="[
                      'text-sm font-medium',
                      step.completed || step.active ? 'text-gray-900' : 'text-gray-400'
                    ]"
                  >
                    {{ $t(`orders.step.${step.key}`) }}
                  </p>
                  <p v-if="step.date" class="text-xs text-gray-500 mt-0.5">{{ step.date }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Shipment Tracking -->
        <div v-if="shipments.length > 0" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.tracking') }}</h2>
          <div v-for="s in shipments" :key="s.id" class="mb-6 last:mb-0 border border-gray-200 rounded-lg p-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
              <div>
                <span class="text-gray-500">Carrier:</span>
                <span class="ml-2 font-medium">{{ s.carrier }}</span>
              </div>
              <div>
                <span class="text-gray-500">Tracking #:</span>
                <a v-if="s.tracking_url" :href="s.tracking_url" target="_blank" class="ml-2 font-medium text-indigo-600 hover:underline">
                  {{ s.tracking_number }}
                </a>
                <span v-else class="ml-2 font-medium text-indigo-600">{{ s.tracking_number }}</span>
              </div>
              <div>
                <span class="text-gray-500">Status:</span>
                <span class="ml-2 font-medium">{{ s.status }}</span>
              </div>
              <div v-if="s.estimated_delivery">
                <span class="text-gray-500">Estimated:</span>
                <span class="ml-2 font-medium">{{ formatDate(s.estimated_delivery) }}</span>
              </div>
            </div>
            <!-- Events Timeline -->
            <div v-if="(s.events || []).length > 0" class="relative pl-6 border-l-2 border-gray-200 space-y-4">
              <div v-for="(evt, ei) in s.events" :key="ei" class="relative">
                <div class="absolute -left-[25px] w-3 h-3 rounded-full border-2 border-indigo-500 bg-white"></div>
                <p class="text-sm font-medium text-gray-900">{{ evt.status || evt.description || evt.label || 'Update' }}</p>
                <p class="text-xs text-gray-500">{{ evt.location || '' }}</p>
                <p class="text-xs text-gray-400">{{ formatDateTime(evt.timestamp || evt.date || evt.time) }}</p>
              </div>
            </div>
            <p v-else class="text-sm text-gray-500 italic">No events recorded yet</p>
          </div>
        </div>
        <div v-else-if="!loading" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ $t('orders.tracking') }}</h2>
          <p class="text-sm text-gray-500">Shipment info pending</p>
        </div>

        <!-- Order Items -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.items') }}</h2>
          <ul class="divide-y divide-gray-200">
            <li
              v-for="(item, idx) in (order.items || order.products || [])"
              :key="idx"
              class="py-4 flex items-center"
            >
              <div class="h-16 w-16 rounded-md bg-gray-100 overflow-hidden flex-shrink-0">
                <img
                  v-if="item.image || item.product_image"
                  :src="item.image || item.product_image"
                  :alt="item.name || item.product_name"
                  class="h-full w-full object-cover"
                />
                <div v-else class="h-full w-full flex items-center justify-center text-gray-400">
                  <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <p class="text-sm font-medium text-gray-900">{{ item.name || item.product_name }}</p>
                <p class="text-sm text-gray-500 mt-0.5">{{ $t('orders.qty') }}: {{ item.quantity }}</p>
              </div>
              <div class="text-right">
                <p class="text-sm font-medium text-gray-900">{{ formatPrice(item.price || item.unit_price) }}</p>
                <p class="text-sm text-gray-500 mt-0.5">{{ formatPrice((item.price || item.unit_price) * item.quantity) }}</p>
              </div>
            </li>
          </ul>
        </div>

        <!-- Order Summary -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.orderSummary') }}</h2>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">{{ $t('orders.subtotal') }}</dt>
              <dd class="text-gray-900">{{ formatPrice(order.subtotal || order.sub_total) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">{{ $t('orders.tax') }}</dt>
              <dd class="text-gray-900">{{ formatPrice(order.tax || 0) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">{{ $t('orders.shipping') }}</dt>
              <dd class="text-gray-900">{{ formatPrice(order.shipping_cost || order.shipping || 0) }}</dd>
            </div>
            <div v-if="order.discount || order.coupon_discount" class="flex justify-between text-green-600">
              <dt>{{ $t('orders.discount') }}</dt>
              <dd>-{{ formatPrice(order.discount || order.coupon_discount || 0) }}</dd>
            </div>
            <div class="flex justify-between border-t border-gray-200 pt-2 mt-2">
              <dt class="text-base font-semibold text-gray-900">{{ $t('orders.total') }}</dt>
              <dd class="text-base font-semibold text-gray-900">{{ formatPrice(order.total || order.total_amount) }}</dd>
            </div>
          </dl>
        </div>

        <!-- Shipping Address -->
        <div v-if="order.shipping_address" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.shippingAddress') }}</h2>
          <address class="text-sm text-gray-600 not-italic">
            <p class="font-medium text-gray-900">{{ order.shipping_address.name || order.shipping_address.recipient_name }}</p>
            <p>{{ order.shipping_address.line1 || order.shipping_address.address_line1 }}</p>
            <p v-if="order.shipping_address.line2 || order.shipping_address.address_line2">
              {{ order.shipping_address.line2 || order.shipping_address.address_line2 }}
            </p>
            <p>
              {{ order.shipping_address.city }}
              <template v-if="order.shipping_address.state">, {{ order.shipping_address.state }}</template>
              {{ order.shipping_address.postal_code || order.shipping_address.zip }}
            </p>
            <p>{{ order.shipping_address.country }}</p>
          </address>
        </div>
      </template>
    </div>

    <!-- Cancel Order Modal -->
    <div v-if="showCancelModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showCancelModal = false"></div>
        <div class="relative bg-white rounded-lg max-w-md w-full p-6 shadow-xl">
          <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('orders.cancelOrderTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-6">
            {{ $t('orders.cancelConfirmText') }}
          </p>
          <div class="flex justify-end space-x-3">
            <button
              @click="showCancelModal = false"
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              @click="doCancelOrder"
              :disabled="cancelling"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
            >
              {{ cancelling ? $t('orders.cancelling') : $t('orders.cancelOrder') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import OrderStatusBadge from '~/components/OrderStatusBadge.vue'
import { useOrderStore } from '~/stores/order'
import { useApi } from '~/composables/useApi'
import { useCurrency } from '~/composables/useCurrency'

definePageMeta({
  middleware: 'auth',
})

const route = useRoute()
const orderStore = useOrderStore()
const { fetchShipments, cancelOrder } = useApi()
const order = ref<any>(null)
const shipments = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const showCancelModal = ref(false)
const cancelling = ref(false)

const orderId = computed(() => route.params.id as string)

const canCancel = computed(() => {
  if (!order.value) return false
  const status = (order.value.status || '').toLowerCase()
  return status === 'pending' || status === 'processing'
})

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const { formatPrice } = useCurrency()

const orderSteps = computed(() => {
  if (!order.value) return []
  const status = (order.value.status || '').toLowerCase()
  const steps = [
    { key: 'ordered', completed: false, active: false, date: '' },
    { key: 'processing', completed: false, active: false, date: '' },
    { key: 'shipped', completed: false, active: false, date: '' },
    { key: 'delivered', completed: false, active: false, date: '' },
  ]

  const statusOrder = ['ordered', 'processing', 'shipped', 'delivered']
  const currentIdx = statusOrder.indexOf(status)

  if (currentIdx >= 0) {
    for (let i = 0; i < steps.length; i++) {
      if (i < currentIdx) steps[i].completed = true
      else if (i === currentIdx) steps[i].active = true
    }
  } else if (status === 'cancelled') {
    steps[0].active = false
    steps[0].completed = true
  }

  return steps
})

const shipmentTimelineEvents = computed(() => {
  const allEvents: { label: string; timestamp: string; location?: string }[] = []
  for (const s of shipments.value) {
    const evts = s.events || []
    for (const e of evts) {
      allEvents.push({
        label: e.status || e.description || e.label || 'Update',
        timestamp: e.timestamp || e.date || e.time || '',
        location: e.location || '',
      })
    }
  }
  return allEvents.sort((a, b) => {
    if (!a.timestamp) return 1
    if (!b.timestamp) return -1
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  })
})

const doCancelOrder = async () => {
  cancelling.value = true
  try {
    await cancelOrder(orderId.value, 'User requested cancellation')
    order.value.status = 'cancelled'
    showCancelModal.value = false
  } catch (err: any) {
    error.value = err?.data?.detail || err?.message || 'Failed to cancel order'
  } finally {
    cancelling.value = false
  }
}

onMounted(async () => {
  try {
    await orderStore.loadOrderDetail(orderId.value)
    order.value = orderStore.currentOrder
    // Fetch shipments
    try {
      shipments.value = await fetchShipments(orderId.value)
    } catch {
      shipments.value = []
    }
  } catch (err: any) {
    error.value = err?.data?.detail || err?.message || 'Failed to load order'
  } finally {
    loading.value = false
  }
})
</script>