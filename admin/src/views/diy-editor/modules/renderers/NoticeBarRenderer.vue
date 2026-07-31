<template>
  <div
    class="flex items-center gap-2 overflow-hidden px-3 py-2 text-sm"
    :style="{ backgroundColor: config.backgroundColor || '#fff7e6', color: config.textColor || '#fa8c16' }"
  >
    <SvgIcon icon="mdi:bullhorn" class="shrink-0 text-16px" />
    <span class="truncate">{{ config.text || '公告栏（未设置公告文字）' }}</span>
    <SvgIcon v-if="config.closable" icon="mdi:close" class="ml-auto shrink-0 text-14px" />
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
