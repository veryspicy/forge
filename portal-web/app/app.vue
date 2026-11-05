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

// locale -> <html lang dir>：lang 取当前语言码，dir 取 locales 定义（ar=rtl，其余默认 ltr）
const { locale, locales } = useI18n()

const htmlLangDir = computed<{ lang: string; dir: 'ltr' | 'rtl' }>(() => {
  const code = String(locale.value || '')
  const list = (locales.value ?? []) as Array<{ code?: string; dir?: string }>
  const hit = list.find(item => item?.code === code)
  return { lang: code, dir: hit?.dir === 'rtl' ? 'rtl' : 'ltr' }
})

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

// lang/dir 需随语言切换响应式更新：unhead 的 htmlAttrs 不接受 ComputedRef，改用 getter 形式的 useHead
useHead(() => ({
  // 语言与书写方向：lang 供 SEO/辅助阅读，dir 驱动 RTL（ar）与 LTR 布局
  htmlAttrs: { ...htmlLangDir.value },
}))
</script>
