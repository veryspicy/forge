<template>
  <Transition name="drawer">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex justify-end"
    >
      <!-- Backdrop -->
      <div
        class="absolute inset-0 bg-black/40 backdrop-blur-sm"
        @click="close"
      />

      <!-- Drawer Panel -->
      <div class="relative w-full max-w-md bg-white shadow-2xl h-full flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ $t('cart.title') }} ({{ cartStore.itemCount }})
          </h2>
          <button
            class="p-2 text-gray-400 hover:text-gray-600 transition rounded-lg hover:bg-gray-100"
            @click="close"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <!-- Items -->
        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          <div v-if="cartStore.items.length === 0" class="text-center py-12">
            <p class="text-gray-500">{{ $t('cart.emptyTitle') }}</p>
          </div>
          <div
            v-for="item in cartStore.items"
            :key="item.product.id"
            class="flex gap-4"
          >
            <div class="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <img
                v-if="item.product.image"
                :src="item.product.image"
                :alt="item.product.name"
                class="w-full h-full object-cover rounded-lg"
              />
              <span v-else class="text-gray-400 text-xs">{{ $t('cart.noImage') }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-medium text-gray-900 truncate">{{ item.product.name }}</h4>
              <p class="text-sm text-gray-500">{{ formatPrice(item.product.price) }} x {{ item.quantity }}</p>
            </div>
            <button
              class="text-gray-400 hover:text-red-500 transition"
              @click="cartStore.removeItem(item.product.id)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Footer -->
        <div class="border-t px-6 py-4 space-y-3">
          <div class="flex justify-between text-gray-900 font-semibold">
            <span>{{ $t('cart.total') }}</span>
            <span>{{ formatPrice(cartStore.total) }}</span>
          </div>
          <NuxtLink
            to="/cart"
            class="block w-full py-2.5 bg-primary-600 text-white text-center rounded-lg hover:bg-primary-700 transition font-medium"
            @click="close"
          >
            {{ $t('cart.viewCart') }}
          </NuxtLink>
          <NuxtLink
            to="/checkout"
            class="block w-full py-2.5 border border-primary-600 text-primary-600 text-center rounded-lg hover:bg-primary-50 transition font-medium"
            @click="close"
          >
            {{ $t('cart.checkout') }}
          </NuxtLink>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useCartStore } from '~/stores/cart'
import { useCurrency } from '~/composables/useCurrency'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const cartStore = useCartStore()
const { formatPrice } = useCurrency()

function close() {
  emit('close')
}
</script>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.25s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
</style>
