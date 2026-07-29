<template>
  <div class="flex flex-col items-center justify-center gap-1 bg-black py-8 text-gray-400">
    <img v-if="config.poster" :src="config.poster" class="max-h-40 w-full object-cover" alt="poster" />
    <template v-else>
      <SvgIcon icon="mdi:play-circle" class="text-32px" />
      <span class="max-w-full truncate px-4 text-xs">{{ config.url || '视频模块（未设置视频地址）' }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
