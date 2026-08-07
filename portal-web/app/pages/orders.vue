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
        class="bg-white rounded-xl shadow-sm border p-6"
      >
        <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <p class="text-sm text-gray-500">{{ $t('orders.orderId') }}: #{{ order.order_number || order.id }}</p>
            <p class="text-sm text-gray-500">{{ $t('orders.date') }}: {{ formatDate(order.created_at) }}</p>
          </div>
          <span class="px-3 py-1 rounded-full text-xs font-medium" :class="statusClass(order.status)">
            {{ statusLabel(order.status) }}
          </span>
        </div>

        <div class="border-t pt-4 space-y-3">
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
              />
              <span v-else>{{ $t('orders.noImage') }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ item.name }}</p>
              <p class="text-xs text-gray-500">{{ $t('orders.qty') }}: {{ item.quantity }}</p>
            </div>
            <p class="text-sm font-medium text-gray-900">{{ formatPrice(item.price) }}</p>
          </div>
        </div>

        <div class="flex justify-between items-center mt-4 pt-4 border-t">
          <p class="font-semibold text-gray-900">{{ $t('orders.total') }}: {{ formatPrice(order.total) }}</p>
          <button
            class="px-4 py-2 text-sm bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition font-medium"
            @click="viewOrder(order.order_number || order.id)"
          >
            {{ $t('orders.viewDetails') }}
          </button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
const localePath = useLocalePath()
import { useOrderStore } from '~/stores/order'
import { useCurrency } from '~/composables/useCurrency'

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

function statusClass(status: string): string {
  const map: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-blue-100 text-blue-800',
    shipped: 'bg-purple-100 text-purple-800',
    delivered: 'bg-green-100 text-green-800',
    cancelled: 'bg-red-100 text-red-800',
  }
  return map[status] || 'bg-gray-100 text-gray-800'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: t('orders.pending'),
    confirmed: t('orders.confirmed'),
    shipped: t('orders.shipped'),
    delivered: t('orders.delivered'),
    cancelled: t('orders.cancelled'),
  }
  return map[status] || status
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString()
}

function viewOrder(orderNo: string | number) {
  navigateTo(`/orders/${orderNo}`)
}

onMounted(() => {
  orderStore.loadOrders()
})
</script>
