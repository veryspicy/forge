<template>
  <div
    class="flex items-center justify-center text-gray-300"
    :style="{ height: `${config.height || 20}px`, backgroundColor: config.backgroundColor || 'transparent' }"
  >
    <span class="text-xs opacity-0 group-hover:opacity-100">空白 {{ config.height || 20 }}px</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
