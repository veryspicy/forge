<template>
  <section class="px-4 py-3" :style="{ backgroundColor: config.backgroundColor || '#ffffff' }">
    <div class="mx-auto max-w-2xl">
      <div
        class="flex items-center gap-2 bg-gray-100 px-4 py-2.5"
        :class="config.style === 'rounded' ? 'rounded-full' : 'rounded-lg'"
      >
        <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 10a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="keyword"
          type="text"
          class="w-full bg-transparent text-sm outline-none"
          :placeholder="config.placeholder || 'Search products...'"
          @keyup.enter="onSearch"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const localePath = useLocalePath()

defineProps<{ config: any; data?: any }>()
const emit = defineEmits<{ (e: 'search', keyword: string): void }>()

const keyword = ref('')

function onSearch() {
  emit('search', keyword.value)
  if (keyword.value.trim()) {
    navigateTo(localePath(`/products?search=${encodeURIComponent(keyword.value.trim())}`))
  }
}
</script>
