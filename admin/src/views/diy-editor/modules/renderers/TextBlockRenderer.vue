<template>
  <div
    :style="{
      textAlign: config.textAlign || 'left',
      fontSize: `${config.fontSize || 14}px`,
      color: config.color || '#333333',
      backgroundColor: config.backgroundColor || 'transparent',
      padding: `${config.padding ?? 16}px`
    }"
  >
    {{ config.content || '文本模块' }}
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
