<template>
  <section v-if="product" class="mx-auto max-w-6xl px-4 py-4">
    <!-- 纵向：复用商品卡片 -->
    <div v-if="config.layout !== 'horizontal'" class="mx-auto max-w-xs">
      <ProductCard :product="product" />
    </div>

    <!-- 横向卡片 -->
    <NuxtLink
      v-else
      :to="`/products/${product.slug || product.id}`"
      class="flex items-center gap-4 rounded-xl border bg-white p-4 transition hover:shadow-md"
    >
      <img
        :src="product.images?.[0] || '/images/placeholder.svg'"
        :alt="product.name"
        class="h-28 w-28 rounded-lg object-cover md:h-36 md:w-36"
      />
      <div class="min-w-0 flex-1">
        <h3 class="text-base font-semibold text-gray-900 md:text-lg">{{ product.name }}</h3>
        <p class="mt-1 line-clamp-2 text-sm text-gray-500">{{ product.description }}</p>
        <div class="mt-2 flex items-center gap-2">
          <span class="text-lg font-bold text-primary-700">{{ formatPrice(product.price) }}</span>
          <span class="text-xs text-yellow-500">{{ '★'.repeat(Math.round(product.rating || 0)) }}</span>
        </div>
      </div>
    </NuxtLink>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCurrency } from '~/composables/useCurrency'

const props = defineProps<{ config: any; data?: any }>()

const { formatPrice } = useCurrency()

const product = computed(() => props.data?.product || null)
</script>
