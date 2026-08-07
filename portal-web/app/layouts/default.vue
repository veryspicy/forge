<template>
  <div class="min-h-screen flex flex-col bg-neutral-50 text-neutral-800">
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
