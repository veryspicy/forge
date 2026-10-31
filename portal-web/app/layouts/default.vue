<template>
  <div class="min-h-screen flex flex-col bg-neutral-50 dark:bg-stone-950 text-neutral-800 dark:text-neutral-200">
    <AppHeader />
    <main class="flex-1">
      <slot />
    </main>
    <PetChatWidget />
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
// Layout provides the shell - Header + Footer + Chat Widget
</script>
