<template>
  <section v-if="slides.length" class="diy-banner relative w-full overflow-hidden">
    <div
      class="relative h-44 w-full sm:h-56 md:h-72"
      :style="{ height: `min(${config.height || 375}px, 50vw)` }"
    >
      <div
        v-for="(slide, i) in slides"
        :key="i"
        class="absolute inset-0 transition-opacity duration-700"
        :class="i === current ? 'opacity-100' : 'pointer-events-none opacity-0'"
      >
        <NuxtLink v-if="slide.link" :to="slide.link" class="block h-full w-full">
          <img :src="slide.image" :alt="`banner-${i}`" class="h-full w-full object-cover" />
        </NuxtLink>
        <img v-else :src="slide.image" :alt="`banner-${i}`" class="h-full w-full object-cover" />
      </div>

      <!-- 指示点 -->
      <div v-if="slides.length > 1" class="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
        <button
          v-for="(_, i) in slides"
          :key="i"
          class="h-2 rounded-full transition-all"
          :class="i === current ? 'w-5 bg-white' : 'w-2 bg-white/50'"
          @click="current = i"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps<{ config: any; data?: any }>()

const slides = computed(() => (props.config.slides || []).filter((s: any) => s.image))
const current = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (props.config.autoplay && slides.value.length > 1) {
    timer = setInterval(() => {
      current.value = (current.value + 1) % slides.value.length
    }, props.config.interval || 3000)
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
