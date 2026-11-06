<script setup lang="ts">
// 统一富文本渲染容器：后台录入的 HTML（CMS 页面 / 商品详情 / DIY）一律经此组件落 DOM，
// 保证「排版基线 + 媒体约束」只有一处实现。
// 样式基线：app/assets/css/main.css → .prose-forge（17px / 1.75 行高 / 68ch，浅深两套主题变量）；
// 媒体约束：同文件 .rich-content（小图铺满、大图限宽 1080 居中）。
// 安全：内容来自后台管理员录入（受权限保护），HTML 净化在后端写入侧执行，前端不再二次转义。
withDefaults(
  defineProps<{
    html?: string | null
    /** prose=限宽 68ch（正文阅读宽度）；full=铺满父容器（宽屏版式区块） */
    width?: 'prose' | 'full'
  }>(),
  { html: '', width: 'prose' },
)
</script>

<template>
  <div
    v-if="html"
    class="rich-content prose prose-neutral prose-forge"
    :class="width === 'full' ? 'max-w-none' : ''"
    v-html="html"
  />
</template>
