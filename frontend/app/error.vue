<template>
  <div class="min-h-screen flex items-center justify-center bg-neutral-50">
    <div class="text-center px-4">
      <h1 class="text-8xl font-bold text-neutral-200 mb-4">{{ error.statusCode }}</h1>
      <p class="text-xl text-neutral-500 mb-8">
        {{ error.message || '页面不存在' }}
      </p>
      <NuxtLink
        :to="localePath('/')"
        class="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
      >
        {{ $t('common.backHome') }}
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NuxtError } from '#app';

const props = defineProps<{
  error: NuxtError;
}>();

const localePath = useLocalePath();
</script>
