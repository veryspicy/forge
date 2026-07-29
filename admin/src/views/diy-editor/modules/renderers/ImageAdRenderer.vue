<template>
  <div :class="config.mode === 'card' ? 'p-2' : ''">
    <div
      class="flex flex-col items-center justify-center gap-1 overflow-hidden bg-gray-100 text-gray-400"
      :class="config.mode === 'card' ? 'rounded' : ''"
      :style="{ height: `${Math.min(config.height || 200, 300)}px` }"
    >
      <img v-if="config.image" :src="config.image" class="h-full w-full object-cover" alt="ad" />
      <template v-else>
        <SvgIcon icon="mdi:image" class="text-32px" />
        <span class="text-xs">图片广告 · {{ config.mode === 'card' ? '卡片' : '通栏' }} · {{ config.height || 200 }}px</span>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
