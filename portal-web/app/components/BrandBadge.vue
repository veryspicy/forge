<template>
  <NuxtLink
    to="/"
    data-brand-name
    class="flex items-center gap-2.5 flex-shrink-0 min-w-0"
    :style="brandNameStyle"
  >
    <!-- Logo 容器：image / svg / text 三分支，与 admin 品牌预览一致 -->
    <span
      class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden"
    >
      <img
        v-if="showLogoImage"
        :src="brandLogo.data"
        :alt="brandName"
        class="max-h-full max-w-full object-contain"
        @error="logoError = true"
      />
      <span
        v-else-if="showLogoSvg"
        class="flex h-full w-full items-center justify-center [&>svg]:h-6 [&>svg]:w-auto"
        v-html="sanitizedBrandSvg"
      />
      <span
        v-else
        class="px-1 text-center text-sm font-semibold text-gray-700 dark:text-gray-200"
      >
        {{ brandName }}
      </span>
    </span>
    <!-- 品牌名称 + 品牌标语（三元素缺一不可） -->
    <span class="min-w-0 flex-1 flex flex-col justify-center leading-tight">
      <span class="truncate text-sm font-semibold text-gray-800 dark:text-gray-100">
        {{ brandName }}
      </span>
      <span v-if="brandTagline" class="truncate text-xs text-gray-500">{{ brandTagline }}</span>
      <span v-else class="text-xs text-gray-400">品牌标语（未设置）</span>
    </span>
  </NuxtLink>
</template>

<script setup lang="ts">
import { useSiteProfile } from '~/composables/useSiteProfile'

const { profile } = useSiteProfile()

const logoError = ref(false)
const brandName = computed(() => profile.value.brand.name || 'Forge')
const brandLogo = computed(() => profile.value.brand.logo ?? { type: 'text', data: '' })
const brandTagline = computed(() => profile.value.brand.tagline || '')
// 品牌文字颜色：auto=跟随主题主色（主题变化时随之变化）；#hex=自定义固定颜色
const brandNameColor = computed(() => {
  const c = profile.value.brand?.nameColor
  if (c && c !== 'auto' && /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(c)) return c
  return profile.value.theme?.primaryColor || '#4f46e5'
})
const brandNameStyle = computed(() => ({ color: brandNameColor.value }))
const showLogoImage = computed(() => brandLogo.value.type === 'image' && !!brandLogo.value.data && !logoError.value)
const showLogoSvg = computed(() => brandLogo.value.type === 'svg' && !!brandLogo.value.data && !logoError.value && isSvgLogoUsable.value)
// SVG 合法性校验：仅当 data 包含 <svg 标记时才按 SVG 渲染，否则回退品牌文字
const isSvgLogoUsable = computed(() => /<svg[\s>]/i.test(brandLogo.value.data || ''))
const sanitizedBrandSvg = computed(() => {
  const raw = brandLogo.value.data || ''
  return raw
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    .trim()
})
// 程序化图片预加载兜底：SSR 首屏 <img> 的 error 事件可能在 hydration 前触发而丢失，
// 依赖原生 @error 不可靠；这里用 new Image() 主动探测，失败立即回退品牌文字。
const LOGO_URL_RE = /^(https?:\/\/|\/|data:image)/i
watch(
  () => brandLogo.value.data,
  (val) => {
    logoError.value = false
    if (!val || brandLogo.value.type !== 'image') return
    if (import.meta.client) {
      if (!LOGO_URL_RE.test(val)) {
        logoError.value = true
        return
      }
      const img = new Image()
      img.onload = () => { logoError.value = false }
      img.onerror = () => { logoError.value = true }
      img.src = val
    }
  },
  { immediate: true },
)
</script>
