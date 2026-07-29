<template>
  <!-- Skeleton loading state -->
  <div
    v-if="!product"
    class="surface-elevated rounded-xl overflow-hidden animate-pulse"
  >
    <div class="h-48 skeleton" />
    <div class="p-4 space-y-3">
      <div class="h-3 w-16 skeleton rounded" />
      <div class="h-5 w-3/4 skeleton rounded" />
      <div class="h-6 w-1/3 skeleton rounded" />
      <div class="h-4 w-1/2 skeleton rounded" />
    </div>
  </div>

  <!-- Product card -->
  <NuxtLink
    v-else
    :to="`/products/${product.slug || product.id}`"
    class="surface-elevated rounded-xl overflow-hidden block relative group transition-all duration-300 ease-out-expo hover:shadow-lg hover:-translate-y-1"
  >
    <!-- Image area -->
    <div class="h-48 bg-neutral-200 flex items-center justify-center text-neutral-400 text-sm overflow-hidden">
      <img
        :src="product.images?.[0] || '/images/placeholder.svg'"
        :alt="product.name"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        @error="(e) => { (e.target as HTMLImageElement).src = '/images/placeholder.svg' }"
      />
    </div>

    <!-- AI recommended badge -->
    <span
      v-if="product.tags?.includes('ai-recommended') || product.is_ai_generated"
      class="absolute top-2 left-2 bg-secondary-500 text-white text-xs font-medium px-2 py-0.5 rounded-full"
    >
      {{ $t('products.aiPick') }}
    </span>

    <!-- Out of stock overlay -->
    <div
      v-if="product.inventory != null && product.inventory <= 0"
      class="absolute inset-0 bg-neutral-950/50 flex items-center justify-center"
    >
      <span class="text-white font-semibold">{{ $t('products.outOfStock') }}</span>
    </div>

    <!-- Info area -->
    <div class="p-4">
      <!-- Category label -->
      <p class="text-xs text-neutral-500 uppercase tracking-wide">
        {{ product.category || $t('products.uncategorized') }}
      </p>

      <!-- Product name -->
      <h3 class="font-heading font-semibold text-neutral-800 truncate mt-1">
        {{ product.name }}
      </h3>

      <!-- Price row -->
      <div class="flex items-center gap-2 mt-2">
        <span class="text-lg font-bold text-primary-600">
          {{ formatPrice(product.price) }}
        </span>
        <span
          v-if="product.discount"
          class="text-sm text-neutral-400 line-through"
        >
          {{ formatPrice(product.original_price) }}
        </span>
        <span
          v-if="product.discount"
          class="text-xs bg-accent-100 text-accent-700 px-1.5 py-0.5 rounded font-medium"
        >
          -{{ product.discount }}%
        </span>
      </div>

      <!-- Rating -->
      <div class="flex items-center gap-1 text-sm mt-1.5">
        <span class="text-secondary-400">
          {{ '★'.repeat(Math.floor(product.rating || 0)) }}
        </span>
        <span class="text-neutral-300">
          {{ '☆'.repeat(5 - Math.floor(product.rating || 0)) }}
        </span>
        <span class="text-neutral-500 ml-1">({{ product.review_count || 0 }})</span>
      </div>

      <!-- Inventory status -->
      <div class="flex items-center gap-1.5 text-xs mt-2">
        <span
          class="w-2 h-2 rounded-full"
          :class="inventoryDotClass"
        />
        <span>{{ inventoryLabel }}</span>
      </div>
    </div>

    <!-- Add to cart hover button -->
    <button
      class="absolute bottom-0 left-0 right-0 bg-primary-600 text-white text-sm font-medium py-2.5 text-center opacity-0 group-hover:opacity-100 hover:bg-primary-700 transition-all translate-y-full group-hover:translate-y-0"
      @click.prevent="addToCart"
    >
      {{ $t('products.addToCart') }}
    </button>
  </NuxtLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCartStore } from '~/stores/cart'
import { useCurrency } from '~/composables/useCurrency'

const props = defineProps<{
  product: any
}>()

const cartStore = useCartStore()
const { t } = useI18n()
const { formatPrice } = useCurrency()
const { toast } = useToast()

const inventoryDotClass = computed(() => {
  const inv = props.product?.inventory
  if (inv == null || inv <= 0) return 'bg-error'
  if (inv <= 5) return 'bg-warning'
  return 'bg-success'
})

const inventoryLabel = computed(() => {
  const inv = props.product?.inventory
  if (inv == null || inv <= 0) return t('products.outOfStock')
  if (inv <= 5) return t('products.lowStock')
  return t('products.inStock')
})

function addToCart() {
  const p = props.product
  cartStore.addItem({
    product: {
      id: String(p.id || p.product_id),
      name: p.name,
      price: Number(p.price) || 0,
      image: p.images?.[0] || p.image || '',
    },
    quantity: 1,
  })
  toast.success(t('products.addedToCart', { name: p.name }))
}
</script>
