<template>
  <div class="p-2">
    <div
      class="flex items-center gap-3 rounded-lg bg-gradient-to-r from-red-400 to-orange-400 p-3 text-white"
      :class="config.style === 'banner' ? 'rounded-none' : ''"
    >
      <div class="text-2xl font-bold">¥--</div>
      <div class="flex-1 text-xs opacity-90">
        <div class="font-semibold">优惠券</div>
        <div>{{ config.couponId ? `ID: ${config.couponId}` : '未选择优惠券' }}</div>
      </div>
      <div class="rounded-full bg-white px-3 py-1 text-xs font-semibold text-red-500">领取</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ config: any }>();
</script>
