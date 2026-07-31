<template>
  <div :style="{ padding: `${config.margin || 0}px 16px` }">
    <hr
      :style="{
        borderTopWidth: `${config.height || 1}px`,
        borderTopStyle: config.style || 'solid',
        borderTopColor: config.color || '#e5e5e5'
      }"
      class="border-x-0 border-b-0"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
