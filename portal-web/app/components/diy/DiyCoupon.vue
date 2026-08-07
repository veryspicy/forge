<template>
  <section class="px-4 py-2" :class="config.style === 'banner' ? '' : 'mx-auto max-w-6xl'">
    <div
      class="flex items-center gap-4 bg-gradient-to-r from-red-500 to-orange-400 p-4 text-white"
      :class="config.style === 'banner' ? '' : 'rounded-xl shadow-sm'"
    >
      <div class="text-3xl font-extrabold">
        {{ coupon?.discount_text || '¥--' }}
      </div>
      <div class="min-w-0 flex-1 text-sm opacity-95">
        <div class="font-semibold">{{ coupon?.name || 'Coupon' }}</div>
        <div class="truncate text-xs opacity-80">{{ coupon?.description || 'Grab it before it expires' }}</div>
      </div>
      <button
        class="shrink-0 rounded-full bg-white px-4 py-1.5 text-sm font-bold text-red-500 transition hover:bg-red-50"
        @click="claimed = true"
      >
        {{ claimed ? 'Claimed' : 'Claim' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{ config: any; data?: any }>()

const claimed = ref(false)
const coupon = computed(() => props.data?.coupon || null)
</script>
