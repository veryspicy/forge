<template>
  <div class="p-2">
    <div class="mb-2 flex gap-2 overflow-x-auto">
      <span
        v-for="(tab, i) in config.tabs || []"
        :key="i"
        class="whitespace-nowrap rounded-full px-3 py-1 text-xs"
        :class="i === 0 ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500'"
      >
        {{ tab.name || `Tab ${i + 1}` }}
      </span>
    </div>
    <div class="grid gap-2" :style="{ gridTemplateColumns: `repeat(${config.columns || 2}, 1fr)` }">
      <div
        v-for="n in Math.min(config.displayCount || 4, 4)"
        :key="n"
        class="flex aspect-square items-center justify-center rounded bg-gray-100"
      >
        <SvgIcon icon="mdi:view-grid" class="text-24px text-gray-300" />
      </div>
    </div>
    <div class="mt-1 text-center text-xs text-gray-400">商品分组 · {{ (config.tabs || []).length }} 个 Tab</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
