﻿<!-- Forge — App Root -->
<template>
  <NuxtLayout>
    <NuxtPage :transition="{ name: 'page', mode: 'out-in' }" />
  </NuxtLayout>
  <!-- Toast container -->
  <div class="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        :class="t.type === 'success' ? 'bg-green-600' : 'bg-red-600'"
        class="text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-xs"
      >
        {{ t.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { useToast } from './composables/useToast'
import { useSiteProfile } from './composables/useSiteProfile'
const { toasts } = useToast()
const { profile } = useSiteProfile()

const faviconLink = computed(() => {
  const favicon = profile.value.brand?.favicon
  if (!favicon) return []
  return [
    { rel: 'icon', type: 'image/x-icon', href: favicon },
    { rel: 'shortcut icon', type: 'image/x-icon', href: favicon },
  ]
})

useHead({
  titleTemplate: "%s | Forge Shop",
  meta: [
    { name: "description", content: "AI-Powered Pet Supplies Store" },
  ],
  link: faviconLink,
});
</script>
