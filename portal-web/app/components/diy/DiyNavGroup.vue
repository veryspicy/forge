<template>
  <section v-if="items.length" class="mx-auto max-w-6xl px-4 py-6">
    <h2 v-if="config.title" class="mb-4 text-xl font-bold text-gray-900">{{ config.title }}</h2>
    <div
      class="diy-nav-grid grid gap-4"
      :style="{ '--cols': String(config.columns || 4), '--mcols': String(Math.min(config.columns || 4, 4)) }"
    >
      <NuxtLink
        v-for="(item, i) in items"
        :key="i"
        :to="item.link || '#'"
        class="group flex flex-col items-center gap-2"
      >
        <div
          class="flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 text-lg font-bold text-primary-600 transition group-hover:bg-primary-100 md:h-14 md:w-14"
        >
          {{ (item.text || '?').charAt(0) }}
        </div>
        <span class="text-center text-xs text-gray-700 md:text-sm">{{ item.text }}</span>
      </NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ config: any; data?: any }>()

const items = computed(() => (props.config.items || []).filter((i: any) => i.text))
</script>

<style scoped>
.diy-nav-grid {
  grid-template-columns: repeat(var(--mcols, 4), minmax(0, 1fr));
}

@media (min-width: 768px) {
  .diy-nav-grid {
    grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr));
  }
}
</style>
