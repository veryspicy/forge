<template>
  <!-- 内容来自后台管理员输入（受权限保护），直接渲染 HTML -->
  <section class="diy-rich-text prose max-w-none" :style="{ padding: `${config.padding ?? 16}px` }" v-html="config.content" />
</template>

<script setup lang="ts">
defineProps<{ config: any; data?: any }>()
</script>
