<script setup lang="ts">
defineOptions({
  name: 'GlobalFooter'
});
</script>

<template>
  <DarkModeContainer class="h-full flex-center">
    <span>Copyright MIT © 2021 Forge</span>
  </DarkModeContainer>
</template>

<style scoped>
:deep(.bg-container.text-base-text.transition-300.h-full.flex-center) {
  width: 600px;
}
</style>
