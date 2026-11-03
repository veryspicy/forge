<script setup lang="ts">
definePageMeta({ layout: 'default' })
const slug = 'story'
</script>
<template>
  <ContentPage :slug="slug" fallback-title="Our Story" />
</template>
