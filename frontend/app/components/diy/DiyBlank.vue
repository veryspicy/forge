<template>
  <div :style="{ height: `${config.height || 20}px`, backgroundColor: config.backgroundColor || 'transparent' }" />
</template>

<script setup lang="ts">
defineProps<{ config: any; data?: any }>()
</script>
