<template>
  <section
    v-if="!closed && config.text"
    class="relative flex items-center gap-2 overflow-hidden px-4 py-2 text-sm"
    :style="{ backgroundColor: config.backgroundColor || '#fff7e6', color: config.textColor || '#fa8c16' }"
  >
    <svg class="h-4 w-4 shrink-0" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2a7 7 0 00-7 7v3.5L3 16v1h18v-1l-2-3.5V9a7 7 0 00-7-7zm0 20a3 3 0 003-3H9a3 3 0 003 3z" />
    </svg>
    <div class="relative flex-1 overflow-hidden">
      <div class="notice-marquee whitespace-nowrap" :style="{ animationDuration: `${Math.max(config.text.length / (config.speed || 50) * 10, 8)}s` }">
        <span class="pr-16">{{ config.text }}</span>
        <span class="pr-16">{{ config.text }}</span>
      </div>
    </div>
    <button v-if="config.closable" class="shrink-0 opacity-60 transition hover:opacity-100" @click="closed = true">
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ config: any; data?: any }>()

const closed = ref(false)
</script>

<style scoped>
.notice-marquee {
  display: inline-block;
  animation-name: diy-notice-scroll;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

@keyframes diy-notice-scroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}
</style>
