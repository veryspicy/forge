<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-3xl font-bold text-gray-900">{{ $t('products.title') }}</h1>
      <button
        class="lg:hidden px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm font-medium"
        @click="showFilters = !showFilters"
      >
        {{ $t('products.filters') }}
      </button>
    </div>

    <div class="flex gap-8">
      <!-- Filter Sidebar -->
      <aside
        class="w-64 flex-shrink-0 hidden lg:block"
        :class="{ 'fixed inset-0 z-50 bg-white p-6 overflow-y-auto lg:relative': showFilters }"
      >
        <FilterSidebar v-model="filters" @update:model-value="applyFilters" />
      </aside>

      <!-- Product Grid -->
      <div class="flex-1 min-w-0">
        <!-- Sort Bar -->
        <div class="flex items-center justify-between mb-6">
          <p class="text-sm text-gray-500">
            {{ $t('products.showingCount', { count: productStore.products.length }) }}
          </p>
          <select
            v-model="sortBy"
            class="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            @change="applyFilters"
          >
            <option value="popular">{{ $t('products.sortPopular') }}</option>
            <option value="price-low">{{ $t('products.sortPriceLow') }}</option>
            <option value="price-high">{{ $t('products.sortPriceHigh') }}</option>
            <option value="rating">{{ $t('products.sortRating') }}</option>
            <option value="newest">{{ $t('products.sortNewest') }}</option>
          </select>
        </div>

        <!-- Loading -->
        <div v-if="productStore.loading" class="text-center py-12 text-gray-500">
          {{ $t('common.loading') }}
        </div>

        <!-- Grid -->
        <div
          v-else-if="productStore.products.length > 0"
          class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          <ProductCard
            v-for="product in productStore.products"
            :key="product.id"
            :product="product"
          />
        </div>

        <!-- Empty -->
        <div v-else class="text-center py-16">
          <p class="text-gray-500">{{ $t('products.noProducts') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useProductStore } from '~/stores/product'
import ProductCard from '~/components/products/ProductCard.vue'
import FilterSidebar from '~/components/products/FilterSidebar.vue'

const productStore = useProductStore()
const showFilters = ref(false)
const sortBy = ref('popular')
const filters = ref({})

function applyFilters() {
  productStore.loadProducts({ sort: sortBy.value, ...filters.value } as any)
}

onMounted(() => {
  productStore.loadProducts({ page_size: 12 } as any)
})
</script>
