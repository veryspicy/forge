<template>
  <section
    class="diy-text-block"
    :style="{
      textAlign: config.textAlign || 'left',
      fontSize: `${config.fontSize || 14}px`,
      color: config.color || '#333333',
      backgroundColor: config.backgroundColor || 'transparent',
      padding: `${config.padding ?? 16}px`,
    }"
  >
    {{ config.content }}
  </section>
</template>

<script setup lang="ts">
defineProps<{ config: any; data?: any }>()
</script>
