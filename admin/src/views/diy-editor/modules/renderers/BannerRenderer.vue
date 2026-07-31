<template>
  <div
    class="flex flex-col items-center justify-center gap-1 overflow-hidden bg-gray-100 text-gray-400"
    :style="{ height: `${Math.min(config.height || 375, 400) / 2.5}px` }"
  >
    <template v-if="config.slides?.length && config.slides[0]?.image">
      <img :src="config.slides[0].image" class="h-full w-full object-cover" alt="banner" />
    </template>
    <template v-else>
      <SvgIcon icon="mdi:view-carousel" class="text-32px" />
      <span class="text-xs">轮播横幅 · {{ config.slides?.length || 0 }} 张{{ config.autoplay ? ' · 自动播放' : '' }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
