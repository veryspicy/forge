<template>
  <div class="p-2">
    <div v-if="config.title" class="mb-2 text-sm font-semibold">{{ config.title }}</div>
    <div
      class="grid gap-2"
      :style="{ gridTemplateColumns: `repeat(${config.columns || 2}, 1fr)` }"
    >
      <div
        v-for="n in placeholderCount"
        :key="n"
        class="flex aspect-square flex-col items-center justify-center gap-1 rounded bg-gray-100 text-gray-300"
      >
        <SvgIcon icon="mdi:package-variant" class="text-24px" />
      </div>
    </div>
    <div class="mt-1 text-center text-xs text-gray-400">
      商品列表 · {{ sourceLabel }} · {{ config.displayCount || 6 }} 个
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ config: any }>();

const placeholderCount = computed(() => Math.min(props.config.displayCount || 6, 6));

const sourceLabel = computed(() => {
  const map: Record<string, string> = { manual: '手动选品', category: '分类', ai_recommend: 'AI 推荐' };
  return map[props.config.source] || '手动选品';
});
</script>
