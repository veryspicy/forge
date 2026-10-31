<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">{{ $t('cart.title') }}</h1>

    <div v-if="cartStore.items.length > 0" class="grid lg:grid-cols-3 gap-8">
      <!-- Cart Items -->
      <div class="lg:col-span-2 space-y-4">
        <div
          v-for="item in cartStore.items"
          :key="item.product.id"
          class="bg-white dark:bg-stone-900 rounded-xl shadow-sm border p-4 flex items-center gap-4"
        >
          <div class="w-20 h-20 bg-neutral-100 dark:bg-stone-800 rounded-lg flex items-center justify-center flex-shrink-0">
            <img
              v-if="item.product.image"
              :src="item.product.image"
              :alt="item.product.name"
              class="w-full h-full object-cover rounded-lg"
            />
            <span v-else class="text-neutral-400 dark:text-neutral-400 text-xs">{{ $t('cart.noImage') }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-neutral-900 dark:text-neutral-100 truncate">{{ item.product.name }}</h3>
            <p class="text-sm text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">&nbsp;</p>
            <div class="flex items-center gap-3 mt-2">
              <button
                class="w-8 h-8 rounded-full border border-neutral-300 dark:border-neutral-700 flex items-center justify-center text-neutral-600 dark:text-neutral-400 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-stone-800 transition"
                @click="updateQty(item, item.quantity - 1)"
              >
                -
              </button>
              <span class="text-sm font-medium">{{ item.quantity }}</span>
              <button
                class="w-8 h-8 rounded-full border border-neutral-300 dark:border-neutral-700 flex items-center justify-center text-neutral-600 dark:text-neutral-400 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-stone-800 transition"
                @click="updateQty(item, item.quantity + 1)"
              >
                +
              </button>
            </div>
          </div>
          <div class="text-right flex-shrink-0">
            <p class="font-semibold text-neutral-900 dark:text-neutral-100">{{ formatPrice(item.product.price * item.quantity) }}</p>
            <button
              class="text-xs text-red-500 hover:text-red-700 mt-1 transition"
              @click="cartStore.removeItem(item.product.id)"
            >
              {{ $t('cart.remove') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Cart Summary -->
      <div class="bg-white dark:bg-stone-900 rounded-xl shadow-sm border p-6 h-fit sticky top-24">
        <h3 class="font-semibold text-neutral-900 dark:text-neutral-100 mb-4">{{ $t('cart.summary') }}</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between text-neutral-600 dark:text-neutral-400 dark:text-neutral-400">
            <span>{{ $t('cart.subtotal') }}</span>
            <span>{{ formatPrice(cartStore.total) }}</span>
          </div>
          <div class="flex justify-between text-neutral-600 dark:text-neutral-400 dark:text-neutral-400">
            <span>{{ $t('cart.shipping') }}</span>
            <span>{{ cartStore.total > 50 ? $t('cart.free') : formatPrice(5) }}</span>
          </div>
          <div class="border-t pt-2 mt-2 flex justify-between font-semibold text-neutral-900 dark:text-neutral-100">
            <span>{{ $t('cart.total') }}</span>
            <span>{{ formatPrice(cartStore.total > 50 ? cartStore.total : cartStore.total + 5) }}</span>
          </div>
        </div>
        <NuxtLink
          :to="localePath('/checkout')"
          class="block w-full mt-6 py-3 bg-accent-600 text-white text-center rounded-lg hover:bg-accent-500 transition font-medium"
        >
          {{ $t('cart.checkout') }}
        </NuxtLink>
        <NuxtLink
          :to="localePath('/products')"
          class="block w-full mt-3 py-2 text-accent-600 text-center text-sm hover:underline"
        >
          {{ $t('cart.continueShopping') }}
        </NuxtLink>
      </div>
    </div>

    <!-- Empty Cart -->
    <div v-else class="text-center py-16">
<!-- eslint-disable-next-line vue/no-v-html -->
      <div class="text-5xl mb-4 text-accent-500/70" v-html="emptyStateIcon('cart')" />
      <h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">{{ $t('cart.emptyTitle') }}</h3>
      <p class="text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 mb-6">{{ $t('cart.emptyHint') }}</p>
      <NuxtLink
        :to="localePath('/products')"
        class="inline-block px-6 py-3 bg-accent-600 text-white rounded-lg hover:bg-accent-500 transition font-medium"
      >
        {{ $t('cart.startShopping') }}
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { emptyStateIcon } from '~/utils/iconSvgs'
const localePath = useLocalePath()
import { useCartStore } from '~/stores/cart'
import { useCurrency } from '~/composables/useCurrency'

definePageMeta({
  middleware: 'auth',
})

const cartStore = useCartStore()
const { formatPrice } = useCurrency()

function updateQty(item: { product: any; quantity: number }, newQty: number) {
  if (newQty <= 0) {
    cartStore.removeItem(item.product.id)
  } else {
    cartStore.updateQuantity(item.product.id, newQty)
  }
}

onMounted(() => {
  cartStore.loadCart()
})
</script>
