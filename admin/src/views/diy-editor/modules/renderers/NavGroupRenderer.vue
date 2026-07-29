<template>
  <div class="p-3">
    <div v-if="config.title" class="mb-2 text-sm font-semibold">{{ config.title }}</div>
    <div class="grid gap-2" :style="{ gridTemplateColumns: `repeat(${config.columns || 4}, 1fr)` }">
      <div
        v-for="(item, i) in displayItems"
        :key="i"
        class="flex flex-col items-center gap-1 text-gray-500"
      >
        <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
          <SvgIcon :icon="item.icon || 'mdi:apps'" class="text-20px" />
        </div>
        <span class="text-xs">{{ item.text || '导航' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ config: any }>();

const displayItems = computed(() => {
  const items = props.config.items || [];
  return items.length ? items : Array.from({ length: props.config.columns || 4 }, () => ({}));
});
</script>
