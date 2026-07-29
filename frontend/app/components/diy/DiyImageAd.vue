<template>
  <section v-if="config.image" class="diy-image-ad" :class="config.mode === 'card' ? 'px-4 py-2' : ''">
    <component
      :is="config.link ? 'NuxtLink' : 'div'"
      :to="config.link || undefined"
      class="block overflow-hidden"
      :class="config.mode === 'card' ? 'mx-auto max-w-6xl rounded-xl shadow-sm' : ''"
    >
      <img
        :src="config.image"
        alt="advertisement"
        class="w-full object-cover"
        :style="{ maxHeight: `${config.height || 200}px` }"
      />
    </component>
  </section>
</template>

<script setup lang="ts">
defineProps<{ config: any; data?: any }>()
</script>
