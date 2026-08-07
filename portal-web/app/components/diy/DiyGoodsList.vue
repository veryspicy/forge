<template>
  <section v-if="products.length" class="mx-auto max-w-6xl px-4 py-6">
    <h2 v-if="config.title" class="mb-4 text-xl font-bold text-gray-900 md:text-2xl">
      {{ config.title }}
    </h2>

    <!-- grid 布局 -->
    <div
      v-if="layout === 'grid'"
      class="diy-goods-grid grid grid-cols-2 gap-3 md:gap-4"
      :style="{ '--cols': String(config.columns || 2) }"
    >
      <ProductCard v-for="p in products" :key="p.id" :product="p" />
    </div>

    <!-- list 布局 -->
    <div v-else-if="layout === 'list'" class="flex flex-col gap-3">
      <NuxtLink
        v-for="p in products"
        :key="p.id"
        :to="`/products/${p.slug || p.id}`"
        class="flex gap-4 rounded-xl border bg-white p-3 transition hover:shadow-md"
      >
        <img
          :src="p.images?.[0] || '/images/placeholder.svg'"
          :alt="p.name"
          class="h-20 w-20 rounded-lg object-cover"
        />
        <div class="flex min-w-0 flex-1 flex-col justify-center">
          <h3 class="truncate text-sm font-semibold text-gray-800">{{ p.name }}</h3>
          <p class="mt-0.5 line-clamp-1 text-xs text-gray-500">{{ p.description }}</p>
          <span v-if="config.showPrice !== false" class="mt-1 text-sm font-bold text-primary-700">
            {{ formatPrice(p.price) }}
          </span>
        </div>
      </NuxtLink>
    </div>

    <!-- scroll 布局 -->
    <div v-else class="flex gap-3 overflow-x-auto pb-2">
      <div v-for="p in products" :key="p.id" class="w-40 shrink-0 md:w-48">
        <ProductCard :product="p" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCurrency } from '~/composables/useCurrency'

const props = defineProps<{ config: any; data?: any }>()

const { formatPrice } = useCurrency()

const products = computed(() => props.data?.products || [])
const layout = computed(() => props.config.layout || 'grid')
</script>

<style scoped>
@media (min-width: 768px) {
  .diy-goods-grid {
    grid-template-columns: repeat(var(--cols, 2), minmax(0, 1fr));
  }
}
</style>
