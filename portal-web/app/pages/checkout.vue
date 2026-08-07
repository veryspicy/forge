<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">{{ $t('checkout.title') }}</h1>

    <div class="grid lg:grid-cols-3 gap-8">
      <!-- Checkout Form -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Shipping Address -->
        <div class="bg-white rounded-xl shadow-sm border p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('checkout.shippingAddress') }}</h2>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.firstName') }}</label>
              <input
                v-model="form.firstName"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.lastName') }}</label>
              <input
                v-model="form.lastName"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.address') }}</label>
              <input
                v-model="form.address"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.city') }}</label>
              <input
                v-model="form.city"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.zipCode') }}</label>
              <input
                v-model="form.zipCode"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.country') }}</label>
              <select
                v-model="form.country"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="US">United States</option>
                <option value="UK">United Kingdom</option>
                <option value="DE">Germany</option>
                <option value="FR">France</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Payment Method -->
        <div class="bg-white rounded-xl shadow-sm border p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('checkout.payment') }}</h2>
          <div class="space-y-3">
            <label class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer" :class="form.payment === 'card' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'">
              <input v-model="form.payment" type="radio" value="card" class="text-primary-600 focus:ring-primary-500" />
              <span class="text-sm font-medium text-gray-900">{{ $t('checkout.creditCard') }}</span>
            </label>
            <label class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer" :class="form.payment === 'paypal' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'">
              <input v-model="form.payment" type="radio" value="paypal" class="text-primary-600 focus:ring-primary-500" />
              <span class="text-sm font-medium text-gray-900">{{ $t('checkout.paypal') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Order Summary -->
      <div class="bg-white rounded-xl shadow-sm border p-6 h-fit sticky top-24">
        <h3 class="font-semibold text-gray-900 mb-4">{{ $t('checkout.orderSummary') }}</h3>
        <div class="space-y-3">
          <div
            v-for="item in cartStore.items"
            :key="item.product.id"
            class="flex justify-between text-sm"
          >
            <span class="text-gray-600 truncate mr-2">{{ item.product.name }} x{{ item.quantity }}</span>
            <span class="text-gray-900">{{ formatPrice(item.product.price * item.quantity) }}</span>
          </div>
        </div>
        <div class="border-t mt-4 pt-4 space-y-2 text-sm">
          <div class="flex justify-between text-gray-600">
            <span>{{ $t('checkout.subtotal') }}</span>
            <span>{{ formatPrice(cartStore.total) }}</span>
          </div>
          <div class="flex justify-between text-gray-600">
            <span>{{ $t('checkout.shipping') }}</span>
            <span>{{ cartStore.total > 50 ? $t('checkout.free') : formatPrice(5) }}</span>
          </div>
          <div class="flex justify-between font-semibold text-gray-900 pt-2 border-t">
            <span>{{ $t('checkout.total') }}</span>
            <span>{{ formatPrice(cartStore.total > 50 ? cartStore.total : cartStore.total + 5) }}</span>
          </div>
        </div>
        <button
          class="w-full mt-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium disabled:opacity-50"
          :disabled="submitting"
          @click="placeOrder"
        >
          {{ submitting ? 'Placing Order...' : $t('checkout.placeOrder') }}
        </button>
        <p v-if="error" class="mt-3 text-sm text-red-600 text-center">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useCartStore } from '~/stores/cart'
import { useApi } from '~/composables/useApi'
import { useCurrency } from '~/composables/useCurrency'

definePageMeta({
  middleware: 'auth',
})

const cartStore = useCartStore()
const { formatPrice } = useCurrency()
const { createOrder } = useApi()
const error = ref('')
const submitting = ref(false)
const router = useRouter()

onMounted(() => {
  cartStore.loadCart()
})

const form = reactive({
  firstName: '',
  lastName: '',
  address: '',
  city: '',
  zipCode: '',
  country: 'US',
  payment: 'card',
})

async function placeOrder() {
  error.value = ''
  if (!cartStore.items.length) {
    error.value = 'Cart is empty'
    return
  }
  submitting.value = true
  try {
    const items = cartStore.items.map((item: any) => ({
      product_id: item.product.id,
      quantity: item.quantity,
    }))
    const order = await createOrder({
      items,
      shipping_address: {
        name: `${form.firstName} ${form.lastName}`.trim(),
        line1: form.address,
        line2: '',
        city: form.city,
        state: '',
        postal_code: form.zipCode,
        country: form.country,
        phone: '',
      },
    })
    cartStore.clearCart()
    router.push(`/orders/${order.order_number || order.id}`)
  } catch (err: any) {
    error.value = err?.data?.detail || err?.message || 'Failed to place order'
  } finally {
    submitting.value = false
  }
}
</script>
