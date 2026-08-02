<template>
  <div :style="{ padding: `${config.padding ?? 16}px` }">
    <div v-if="config.content" class="rich-content text-sm" v-html="config.content"></div>
    <div v-else class="flex items-center justify-center gap-1 py-4 text-gray-400">
      <SvgIcon icon="mdi:format-text" class="text-20px" />
      <span class="text-xs">富文本</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
