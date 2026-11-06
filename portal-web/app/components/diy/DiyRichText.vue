<template>
  <!-- 内容来自后台管理员输入（受权限保护），统一由 RichText 渲染以复用 prose-forge 排版基线 -->
  <section :style="{ padding: `${config.padding ?? 16}px` }">
    <RichText :html="config.content" width="full" />
  </section>
</template>

<script setup lang="ts">
defineProps<{ config: any; data?: any }>()
</script>
