<template>
  <div
    class="flex items-center justify-between p-3"
    :style="{ backgroundColor: config.backgroundColor || '#ff4757', color: config.textColor || '#ffffff' }"
  >
    <span class="text-sm font-semibold">{{ config.title || 'Limited Time Offer' }}</span>
    <div class="flex items-center gap-1 text-xs">
      <SvgIcon icon="mdi:timer" class="text-16px" />
      <span class="rounded bg-black/20 px-1.5 py-0.5 font-mono">00:00:00</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
