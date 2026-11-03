<script setup lang="ts">
// CMS 内容页通用组件：按 slug 拉取已发布内容（backend /api/v1/content/{slug}），
// 未发布/不存在时降级为 Coming soon 占位，并动态设置 SEO。
// 使用 useAsyncData 在 SSR 阶段服务端预取，保证内容可被搜索引擎索引。
import { computed } from 'vue'
import { useApi } from '~/composables/useApi'

const props = defineProps<{ slug: string; fallbackTitle: string }>()

const { t } = useI18n()
const { fetchContent } = useApi()

const {
  data: content,
  pending: loading,
} = await useAsyncData(`content-${props.slug}`, async () => {
  try {
    const res: any = await fetchContent(props.slug)
    return res?.data || null
  } catch {
    return null
  }
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
  <div class="max-w-3xl mx-auto px-4 py-16">
    <h1 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
      {{ content?.title || fallbackTitle }}
    </h1>
    <div v-if="loading" class="text-sm text-neutral-400 dark:text-neutral-400">
      {{ t('common.loading') }}
    </div>
    <div
      v-else-if="content"
      class="prose prose-neutral dark:prose-invert max-w-none text-neutral-600 dark:text-neutral-400"
      v-html="content.body"
    />
    <div
      v-else
      class="prose text-neutral-600 dark:text-neutral-400 dark:text-neutral-400"
    >
      <p>Coming soon.</p>
    </div>
  </div>
</template>
