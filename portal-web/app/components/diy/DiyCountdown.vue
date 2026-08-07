<template>
  <section
    class="flex items-center justify-between px-4 py-3"
    :style="{ backgroundColor: config.backgroundColor || '#ff4757', color: config.textColor || '#ffffff' }"
  >
    <span class="text-sm font-bold md:text-base">{{ config.title || 'Limited Time Offer' }}</span>
    <div class="flex items-center gap-1 font-mono text-sm md:text-base">
      <span class="rounded bg-black/25 px-2 py-0.5">{{ parts.h }}</span>
      <span>:</span>
      <span class="rounded bg-black/25 px-2 py-0.5">{{ parts.m }}</span>
      <span>:</span>
      <span class="rounded bg-black/25 px-2 py-0.5">{{ parts.s }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps<{ config: any; data?: any }>()

const remain = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const parts = computed(() => {
  const total = Math.max(0, Math.floor(remain.value / 1000))
  const h = String(Math.floor(total / 3600)).padStart(2, '0')
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0')
  const s = String(total % 60).padStart(2, '0')
  return { h, m, s }
})

function tick() {
  const end = new Date(props.config.endTime).getTime()
  remain.value = Number.isNaN(end) ? 0 : end - Date.now()
}

onMounted(() => {
  tick()
  timer = setInterval(tick, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
