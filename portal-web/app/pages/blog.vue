<script setup lang="ts">
definePageMeta({ layout: 'default' })
const slug = 'blog'
</script>
<template>
  <ContentPage :slug="slug" fallback-title="Blog" />
</template>
