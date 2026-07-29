<template>
  <div class="p-2">
    <div
      class="flex gap-2 rounded bg-gray-50 p-2"
      :class="config.layout === 'horizontal' ? 'flex-row' : 'flex-col'"
    >
      <div class="flex aspect-square items-center justify-center rounded bg-gray-100" :class="config.layout === 'horizontal' ? 'w-24' : 'w-full'">
        <SvgIcon icon="mdi:card" class="text-32px text-gray-300" />
      </div>
      <div class="flex flex-1 flex-col justify-center gap-1">
        <div class="h-3 w-3/4 rounded bg-gray-200"></div>
        <div class="h-3 w-1/3 rounded bg-gray-200"></div>
      </div>
    </div>
    <div class="mt-1 text-center text-xs text-gray-400">
      单商品卡片 · {{ config.productId ? '已选商品' : '未选择商品' }}
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
