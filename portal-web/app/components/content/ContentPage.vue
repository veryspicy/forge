<script setup lang="ts">
// CMS 内容页通用组件：按 slug + 当前语言拉取已发布内容（backend /api/v1/content/{slug}?locale=），
// 未发布/不存在时降级为 Coming soon 占位，并动态设置 SEO。
// 使用 useAsyncData 在 SSR 阶段服务端预取，保证内容可被搜索引擎索引。
import { computed } from 'vue'
import { useApi } from '~/composables/useApi'

const props = defineProps<{ slug: string; fallbackTitle: string }>()

const { t } = useI18n()
const locale = useI18n().locale
const { fetchContent } = useApi()

const {
  data: content,
  pending: loading,
} = await useAsyncData(`content-${props.slug}-${locale.value}`, async () => {
  try {
    const res: any = await fetchContent(props.slug, locale.value || 'en')
    return res?.data || null
  } catch {
    return null
  }
})

// 正文内的相对链接（如 /contact、/orders）需补上当前语言前缀，
// 否则中文页点击后会被带回英文站点。i18n strategy=prefix，所有语言均有前缀。
const localizedBody = computed(() => {
  const raw: string = content.value?.body || ''
  const current = locale.value || 'en'
  return raw.replace(/href="\/(?!\/)(?![a-z]{2}\/)/gi, `href="/${current}/`)
})

const headTitle = computed(
  () => content.value?.seo_title || content.value?.title || props.fallbackTitle,
)
const headMeta = computed(() =>
  content.value?.seo_description
    ? [{ name: 'description', content: content.value.seo_description }]
    : [],
)

useHead({ title: headTitle, meta: headMeta })
</script>

<template>
  <article class="max-w-3xl mx-auto px-4 py-16 sm:py-20">
    <header class="mb-10 sm:mb-12">
      <h1
        class="font-heading text-4xl sm:text-5xl font-semibold tracking-tight text-primary-900 dark:text-neutral-100"
      >
        {{ content?.title || fallbackTitle }}
      </h1>
      <!-- 装饰短横线：内容页统一的品牌分割符号 -->
      <div class="mt-6 h-px w-16 bg-accent-400 dark:bg-accent-500" />
    </header>
    <div v-if="loading" class="text-sm text-neutral-400 dark:text-neutral-400">
      {{ t('common.loading') }}
    </div>
    <!-- 正文统一走 RichText：prose-forge 排版基线（返回 null 时组件自身不渲染容器） -->
    <RichText v-else-if="content" :html="localizedBody" />
    <p v-else class="text-neutral-500 dark:text-neutral-400">Coming soon.</p>
  </article>
</template>
