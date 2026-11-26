<template>
  <div
    class="min-h-screen flex flex-col bg-neutral-50 dark:bg-stone-950 text-neutral-800 dark:text-neutral-200"
    :class="isChatPage ? 'h-[100dvh] overflow-hidden lg:h-auto lg:overflow-visible' : ''"
  >
    <AppHeader />
    <main class="flex-1" :class="isChatPage ? 'flex flex-col min-h-0 lg:block' : ''">
      <slot />
    </main>
    <PetChatWidget />
    <AppFooter v-if="!isChatPage" />
  </div>
</template>

<script setup lang="ts">
// Layout provides the shell - Header + Footer + Chat Widget
// 聊天页为全屏应用式布局：隐藏页脚，避免页脚参与整页滚动、挤占输入区
const route = useRoute()
const isChatPage = computed(() => /\/chat\/?$/.test(route.path))
</script>
