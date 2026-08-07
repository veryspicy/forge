<template>
  <section v-if="config.url" class="diy-video mx-auto max-w-6xl px-4 py-2">
    <video
      :src="config.url"
      :poster="config.poster || undefined"
      :autoplay="!!config.autoplay"
      :loop="!!config.loop"
      :muted="!!config.autoplay"
      controls
      playsinline
      class="w-full rounded-xl"
    />
  </section>
</template>

<script setup lang="ts">
defineProps<{ config: any; data?: any }>()
</script>
