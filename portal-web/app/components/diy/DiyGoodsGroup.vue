<template>
  <section v-if="tabs.length" class="mx-auto max-w-6xl px-4 py-6">
    <!-- Tab 切换 -->
    <div class="mb-4 flex gap-2 overflow-x-auto">
      <button
        v-for="(tab, i) in tabs"
        :key="i"
        class="whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition"
        :class="i === activeTab ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        @click="activeTab = i"
      >
        {{ tab.name || `Tab ${i + 1}` }}
      </button>
    </div>

    <div
      class="diy-goods-grid grid grid-cols-2 gap-3 md:gap-4"
      :style="{ '--cols': String(config.columns || 2) }"
    >
      <ProductCard v-for="p in activeProducts" :key="p.id" :product="p" />
    </div>
    <div v-if="!activeProducts.length" class="py-8 text-center text-sm text-gray-400">
      No products in this group
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{ config: any; data?: any }>()

const activeTab = ref(0)

const tabs = computed(() => props.data?.tabs || [])
const activeProducts = computed(() => tabs.value[activeTab.value]?.products || [])
</script>

<style scoped>
@media (min-width: 768px) {
  .diy-goods-grid {
    grid-template-columns: repeat(var(--cols, 2), minmax(0, 1fr));
  }
}
</style>
