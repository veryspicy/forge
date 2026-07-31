<template>
  <div class="p-2" :style="{ backgroundColor: config.backgroundColor || '#ffffff' }">
    <div
      class="flex items-center gap-2 bg-gray-100 px-3 py-1.5 text-sm text-gray-400"
      :class="config.style === 'rounded' ? 'rounded-full' : 'rounded'"
    >
      <SvgIcon icon="mdi:magnify" class="text-16px" />
      <span>{{ config.placeholder || 'Search products...' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
