<template>
  <div class="min-h-screen bg-gray-50 py-8">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Loading -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"/>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>

      <template v-else-if="order">
        <!-- Breadcrumb -->
        <nav class="flex mb-6 text-sm text-gray-500">
          <button class="hover:text-gray-700" @click="navigateTo('/orders')">{{ $t('orders.orders') }}</button>
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
                class="px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                @click="showCancelModal = true"
              >
                {{ $t('orders.cancelOrder') }}
              </button>
              <button
                v-if="canConfirmReceipt"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
                @click="doConfirmReceipt"
              >
                {{ $t('orders.confirmReceipt') }}
              </button>
              <button
                v-if="canDeleteOrder"
                class="px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                @click="doDeleteOrder"
              >
                {{ $t('orders.deleteOrder') }}
              </button>
              <button
                v-if="canPay"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                @click="openPayModal"
              >
                {{ $t('orders.pay') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Order Progress -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.tracking') }}</h2>
          <ol class="flex w-full items-start">
            <li
              v-for="(step, idx) in orderSteps"
              :key="step.key"
              class="relative flex-1 flex flex-col items-center min-w-0"
            >
              <div class="flex items-center w-full">
                <div
                  :class="[
                    'h-1 flex-1 rounded-full transition-colors',
                    idx === 0 ? 'bg-transparent' : (orderSteps[idx - 1].completed ? 'bg-indigo-600' : 'bg-gray-200')
                  ]"
                />
                <div
                  :class="[
                    'relative z-10 flex items-center justify-center w-10 h-10 rounded-full border-2 flex-shrink-0',
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
                  />
                  <span v-else class="text-gray-400 text-sm">{{ idx + 1 }}</span>
                </div>
                <div
                  :class="[
                    'h-1 flex-1 rounded-full transition-colors',
                    idx === orderSteps.length - 1 ? 'bg-transparent' : (step.completed ? 'bg-indigo-600' : 'bg-gray-200')
                  ]"
                />
              </div>
              <p
                :class="[
                  'mt-2 px-1 text-center text-sm font-medium leading-tight',
                  step.completed || step.active ? 'text-gray-900' : 'text-gray-400'
                ]"
              >
                {{ $t(`orders.step.${step.key}`) }}
              </p>
              <p v-if="step.date" class="mt-0.5 text-xs text-gray-500">{{ step.date }}</p>
            </li>
          </ol>
        </div>

        <!-- Shipment Tracking -->
        <div v-if="shipments.length > 0" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.shipmentTracking') }}</h2>
          <div v-for="s in shipments" :key="s.id" class="mb-6 last:mb-0 border border-gray-200 rounded-lg p-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
              <div>
                <span class="text-gray-500">{{ $t('orders.carrier') }}:</span>
                <span class="ml-2 font-medium">{{ s.carrier }}</span>
              </div>
              <div>
                <span class="text-gray-500">{{ $t('orders.trackingNumber') }}:</span>
                <a v-if="s.tracking_url" :href="s.tracking_url" target="_blank" class="ml-2 font-medium text-indigo-600 hover:underline">
                  {{ s.tracking_number }}
                </a>
                <span v-else class="ml-2 font-medium text-indigo-600">{{ s.tracking_number }}</span>
              </div>
              <div>
                <span class="text-gray-500">{{ $t('orders.trackingStatus') }}:</span>
                <span class="ml-2 font-medium">{{ s.status }}</span>
              </div>
              <div v-if="s.estimated_delivery">
                <span class="text-gray-500">{{ $t('orders.estimatedDelivery') }}:</span>
                <span class="ml-2 font-medium">{{ formatDate(s.estimated_delivery) }}</span>
              </div>
            </div>
            <!-- Events Timeline -->
            <div v-if="(s.events || []).length > 0" class="relative pl-6 border-l-2 border-gray-200 space-y-4">
              <div v-for="(evt, ei) in s.events" :key="ei" class="relative">
                <div class="absolute -left-[25px] w-3 h-3 rounded-full border-2 border-indigo-500 bg-white"/>
                <p class="text-sm font-medium text-gray-900">{{ evt.status || evt.description || evt.label || $t('orders.trackingUpdate') }}</p>
                <p class="text-xs text-gray-500">{{ evt.location || '' }}</p>
                <p class="text-xs text-gray-400">{{ formatDateTime(evt.timestamp || evt.date || evt.time) }}</p>
              </div>
            </div>
            <p v-else class="text-sm text-gray-500 italic">{{ $t('orders.noTrackingEvents') }}</p>
          </div>
        </div>
        <div v-else-if="!loading && ['shipped', 'delivered'].includes((order.status || '').toLowerCase())" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ $t('orders.shipmentTracking') }}</h2>
          <p class="text-sm text-gray-500">{{ $t('orders.noShipment') }}</p>
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
                >
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
                <div v-if="canReview" class="mt-2">
                  <span v-if="isReviewed(item.id)" class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-500">
                    <svg class="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                    {{ $t('reviews.reviewed') }}
                  </span>
                  <button
                    v-else
                    class="px-3 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                    @click="openReviewModal(item)"
                  >
                    {{ $t('reviews.write') }}
                  </button>
                </div>
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
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="showCancelModal = false"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('orders.cancelOrderTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-6">
            {{ $t('orders.cancelConfirmText') }}
          </p>
          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="showCancelModal = false"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              :disabled="cancelling"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              @click="doCancelOrder"
            >
              {{ cancelling ? $t('orders.cancelling') : $t('orders.cancelOrder') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pay Order Modal -->
    <div v-if="showPayModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="showPayModal = false"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-1">{{ $t('orders.payTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-4">{{ $t('orders.payMockNote') }}</p>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('checkout.paymentMethod') }}</label>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                class="border rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition"
                :class="payForm.method === 'card' ? 'border-indigo-600 ring-1 ring-indigo-600 text-indigo-700' : 'border-gray-300 text-gray-600 hover:border-gray-400'"
                @click="payForm.method = 'card'"
              >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V6a2 2 0 00-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/></svg>
                {{ $t('checkout.creditCard') }}
              </button>
              <button
                type="button"
                class="border rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition"
                :class="payForm.method === 'paypal' ? 'border-indigo-600 ring-1 ring-indigo-600 text-indigo-700' : 'border-gray-300 text-gray-600 hover:border-gray-400'"
                @click="payForm.method = 'paypal'"
              >
                <span class="font-bold italic">Pay<span class="text-blue-600">Pal</span></span>
                {{ $t('checkout.paypal') }}
              </button>
            </div>
          </div>

          <div v-if="payForm.method === 'card'" class="space-y-3 mb-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.cardName') }}</label>
              <input
                v-model.trim="payForm.card.name"
                type="text"
                :placeholder="$t('checkout.fullName')"
                class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.cardNumber') }}</label>
              <input
                v-model.trim="payForm.card.number"
                type="text"
                inputmode="numeric"
                maxlength="19"
                placeholder="4242 4242 4242 4242"
                class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.expiryDate') }}</label>
                <input
                  v-model.trim="payForm.card.expiry"
                  type="text"
                  inputmode="numeric"
                  maxlength="5"
                  placeholder="MM/YY"
                  class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.cardCvv') }}</label>
                <input
                  v-model.trim="payForm.card.cvv"
                  type="password"
                  inputmode="numeric"
                  maxlength="4"
                  placeholder="123"
                  class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
              </div>
            </div>
            <p v-if="cardError" class="text-xs text-red-600">{{ cardError }}</p>
          </div>

          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="showPayModal = false"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              :disabled="paying"
              class="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70"
              @click="doPay"
            >
              <span v-if="paying" class="inline-block w-4 h-4 mr-2 border-2 border-white/40 border-t-white rounded-full animate-spin"/>
              {{ paying ? $t('orders.paying') : $t('orders.pay') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Review Modal -->
    <div v-if="reviewTarget" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="reviewTarget = null"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reviews.write') }} - {{ reviewTarget.name || reviewTarget.product_name }}
          </h3>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('reviews.rating') }}</label>
            <div class="flex gap-1">
              <button
                v-for="star in 5"
                :key="star"
                type="button"
                class="text-2xl focus:outline-none transition"
                :class="star <= reviewForm.rating ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-200'"
                @click="reviewForm.rating = star"
              >
                ★
              </button>
            </div>
            <p v-if="reviewError" class="text-xs text-red-600 mt-1">{{ reviewError }}</p>
          </div>

          <div class="space-y-3 mb-4">
            <input
              v-model.trim="reviewForm.title"
              type="text"
              maxlength="200"
              :placeholder="$t('reviews.titlePlaceholder')"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            >
            <textarea
              v-model.trim="reviewForm.content"
              rows="4"
              maxlength="5000"
              :placeholder="$t('reviews.contentPlaceholder')"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 resize-none"
            />
          </div>

          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="reviewTarget = null"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              :disabled="reviewSubmitting"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              @click="doSubmitReview"
            >
              {{ reviewSubmitting ? $t('reviews.submitting') : $t('reviews.submit') }}
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
const { fetchShipments } = useApi()
const { toMessage, resolveCode } = useApiError()
const { toast } = useToast()
const { t } = useI18n()
const order = ref<any>(null)
const shipments = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const showCancelModal = ref(false)
const cancelling = ref(false)

// ---- Payment ----
const showPayModal = ref(false)
const paying = ref(false)
const cardError = ref('')
const payForm = ref({
  method: 'card' as 'card' | 'paypal',
  card: { name: '', number: '', expiry: '', cvv: '' },
})

// ---- Review ----
const reviewTarget = ref<any>(null)
const reviewSubmitting = ref(false)
const reviewError = ref('')
const reviewForm = ref({ rating: 0, title: '', content: '' })

const orderId = computed(() => route.params.id as string)

const canCancel = computed(() => {
  if (!order.value) return false
  const status = (order.value.status || '').toLowerCase()
  return status === 'pending' || status === 'processing'
})

const canPay = computed(() => {
  if (!order.value) return false
  return (order.value.payment_status === 'unpaid' || (order.value.status || '').toLowerCase() === 'pending') && !order.value.deleted_at
})

const canConfirmReceipt = computed(() => {
  if (!order.value) return false
  return (order.value.status || '').toLowerCase() === 'shipped'
})

const canDeleteOrder = computed(() => {
  if (!order.value) return false
  const status = (order.value.status || '').toLowerCase()
  return (status === 'delivered' || status === 'cancelled') && !order.value.deleted_at
})

const canReview = computed(() => {
  if (!order.value) return false
  const status = (order.value.status || '').toLowerCase()
  return status === 'delivered' && !order.value.deleted_at
})

const isReviewed = (itemId: string) => orderStore.reviewedItemIds.has(String(itemId))

const openPayModal = () => {
  payForm.value = { method: order.value?.payment_method === 'paypal' ? 'paypal' : 'card', card: { name: '', number: '', expiry: '', cvv: '' } }
  cardError.value = ''
  showPayModal.value = true
}

const doPay = async () => {
  cardError.value = ''
  if (payForm.value.method === 'card') {
    const card = payForm.value.card
    if (!card.name || !card.number || !card.expiry || !card.cvv) {
      cardError.value = t('checkout.invalidCard')
      return
    }
  }
  paying.value = true
  try {
    // 模拟真实支付网关跳转/风控耗时，避免“秒付成功”造成不真实感
    await new Promise((resolve) => setTimeout(resolve, 1500))
    await orderStore.payOrder(orderId.value, {
      payment_method: payForm.value.method,
      card: payForm.value.method === 'card' ? { ...payForm.value.card } : undefined,
    })
    showPayModal.value = false
    toast.success(t('orders.paySuccess'))
    await reloadOrder()
  } catch (err: any) {
    cardError.value = toMessage(err)
  } finally {
    paying.value = false
  }
}

const doConfirmReceipt = async () => {
  if (!confirm(t('orders.confirmReceiptHint') as string)) return
  try {
    await orderStore.confirmReceipt(orderId.value)
    toast.success(t('orders.completed'))
    await reloadOrder()
  } catch (err: any) {
    error.value = toMessage(err)
  }
}

const doDeleteOrder = async () => {
  if (!confirm(t('orders.deleteConfirmText') as string)) return
  try {
    await orderStore.deleteOrder(orderId.value)
    toast.success(t('orders.orderDeleted'))
    navigateTo('/orders')
  } catch (err: any) {
    error.value = toMessage(err)
  }
}

const openReviewModal = (item: any) => {
  reviewTarget.value = item
  reviewForm.value = { rating: 0, title: '', content: '' }
  reviewError.value = ''
}

const doSubmitReview = async () => {
  reviewError.value = ''
  if (!reviewTarget.value || reviewForm.value.rating < 1) {
    reviewError.value = t('reviews.rateRequired')
    return
  }
  reviewSubmitting.value = true
  try {
    await orderStore.submitReview({
      order_number: orderId.value,
      order_item_id: String(reviewTarget.value.id),
      rating: reviewForm.value.rating,
      title: reviewForm.value.title || undefined,
      content: reviewForm.value.content || undefined,
    })
    reviewTarget.value = null
    toast.success(t('reviews.success'))
    await orderStore.loadMyReviews()
  } catch (err: any) {
    reviewError.value = toMessage(err)
  } finally {
    reviewSubmitting.value = false
  }
}

const reloadOrder = async () => {
  await orderStore.loadOrderDetail(orderId.value)
  order.value = orderStore.currentOrder
}

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
    { key: 'confirmed', completed: false, active: false, date: '' },
    { key: 'shipped', completed: false, active: false, date: '' },
    { key: 'delivered', completed: false, active: false, date: '' },
  ]

  // 订单状态机：pending(未支付) -> confirmed(已支付待发货) -> shipped(已发货) -> delivered(已确认收货)
  // 对应步骤点亮：下单->已下单；支付->待发货；卖家发货->已发货；确认收货->已确认收货
  const statusOrder = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
  const currentIdx = statusOrder.indexOf(status)

  if (status === 'delivered') {
    steps.forEach((s) => { s.completed = true })
  } else if (currentIdx >= 0) {
    const stepIdx = currentIdx === 0 ? 0 : (currentIdx === 1 || currentIdx === 2 ? 1 : 2)
    for (let i = 0; i < steps.length; i++) {
      if (i < stepIdx) steps[i].completed = true
      else if (i === stepIdx) steps[i].active = true
    }
  } else if (status === 'cancelled') {
    // 已取消：已下单步骤保持完成，其余置灰由模板默认展示
    steps[0].completed = true
  }

  return steps
})

const doCancelOrder = async () => {
  cancelling.value = true
  try {
    await orderStore.cancelOrder(orderId.value, 'User requested cancellation')
    showCancelModal.value = false
    toast.success(t('orders.cancelled'))
    await reloadOrder()
  } catch (err: any) {
    error.value = toMessage(err)
  } finally {
    cancelling.value = false
  }
}

onMounted(async () => {
  try {
    await orderStore.loadOrderDetail(orderId.value)
    order.value = orderStore.currentOrder
    orderStore.loadMyReviews()
    // Fetch shipments
    try {
      shipments.value = await fetchShipments(orderId.value)
    } catch {
      shipments.value = []
    }
    // 列表页“去支付”跳转时自动唤起支付弹窗
    if (route.query.pay === '1' && canPay.value) {
      openPayModal()
    }
  } catch (err: any) {
    const code = resolveCode(err)
    const httpStatus: number | undefined = err?.status ?? err?.response?.status
    if (code === 'NOT_FOUND' || code === 'ORDER_NOT_FOUND' || httpStatus === 404) {
      showError({ statusCode: 404, statusMessage: 'NOT_FOUND' })
      return
    }
    error.value = toMessage(err)
  } finally {
    loading.value = false
  }
})
</script>