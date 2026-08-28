<template>
  <div>
    <section v-if="profile.homeHero.useCarousel" class="carousel-section">
      <div class="relative w-full overflow-hidden">
        <div
          class="flex transition-transform duration-500 ease-in-out"
          :style="{ transform: `translateX(-${activeIndex * 100}%)` }"
        >
          <div
            v-for="(img, idx) in profile.homeHero.carousel.images"
            :key="idx"
            class="relative flex-shrink-0 w-full"
          >
            <NuxtLink
              v-if="img.link"
              :to="localePath(img.link)"
              class="block relative w-full h-[420px] md:h-[500px]"
            >
              <img
                :src="img.url"
                :alt="img.alt || ''"
                class="w-full h-full object-cover"
              />
              <h2
                v-if="img.title"
                class="absolute bottom-6 left-6 text-3xl font-bold text-white drop-shadow-lg"
              >
                {{ img.title }}
              </h2>
            </NuxtLink>
            <div v-else class="relative w-full h-[420px] md:h-[500px]">
              <img
                :src="img.url"
                :alt="img.alt || ''"
                class="w-full h-full object-cover"
              />
              <h2
                v-if="img.title"
                class="absolute bottom-6 left-6 text-3xl font-bold text-white drop-shadow-lg"
              >
                {{ img.title }}
              </h2>
            </div>
          </div>
        </div>

        <button
          v-if="maxIndex > 0"
          @click="prevSlide"
          class="absolute left-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-800 w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition"
          aria-label="Previous slide"
        >
          ‹
        </button>
        <button
          v-if="maxIndex > 0"
          @click="nextSlide"
          class="absolute right-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-800 w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition"
          aria-label="Next slide"
        >
          ›
        </button>

        <div v-if="maxIndex > 0" class="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
          <button
            v-for="(_, idx) in profile.homeHero.carousel.images"
            :key="idx"
            @click="goToSlide(idx)"
            class="w-2.5 h-2.5 rounded-full transition"
            :class="activeIndex === idx ? 'bg-white' : 'bg-white/50 hover:bg-white/70'"
            :aria-label="`Go to slide ${idx + 1}`"
          />
        </div>
      </div>
    </section>

    <section
      v-else
      :class="['hero text-white py-20', heroSectionCls]"
      :style="heroBackgroundStyle"
    >
      <div class="max-w-6xl mx-auto px-4 text-center">
        <h1 class="text-4xl md:text-5xl font-bold mb-4">
          {{ title }}
        </h1>
        <p class="text-lg text-primary-100 mb-8 max-w-2xl mx-auto">
          {{ subtitle }}
        </p>
        <div class="flex justify-center gap-4">
          <NuxtLink
            :to="localePath(cta1To)"
            class="px-6 py-3 bg-white text-primary-700 rounded-lg hover:bg-gray-100 transition font-semibold"
          >
            {{ cta1 }}
          </NuxtLink>
          <NuxtLink
            :to="localePath(cta2To)"
            class="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-400 transition font-semibold border border-primary-300"
          >
            {{ cta2 }}
          </NuxtLink>
        </div>
      </div>
    </section>

    <section
      v-if="hasFeature('show_tailored_pets') && isLoggedIn && petStore.pets.length > 0"
      class="bg-gray-50 py-12"
    >
      <div class="max-w-6xl mx-auto px-4">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900">
            Tailored for Your Pet
          </h2>
          <NuxtLink :to="localePath('/chat')" class="text-sm text-primary-600 hover:text-primary-700 font-medium">
            Ask AI for more →
          </NuxtLink>
        </div>

        <div v-if="recLoading" class="text-center py-8">
          <div class="animate-pulse text-gray-400">Loading personalized recommendations...</div>
        </div>

        <div v-else-if="tailoredProducts.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="product in tailoredProducts"
            :key="product.product_id"
            class="bg-white rounded-xl shadow-sm border hover:shadow-md transition cursor-pointer"
            @click="navigateTo(localePath(`/products/${product.product_id}`))"
          >
            <div class="p-4">
              <div class="w-full h-24 bg-gradient-to-br from-primary-100 to-primary-200 rounded-lg mb-3 flex items-center justify-center">
                <span class="text-3xl">{{ productIcon(product.product_name) }}</span>
              </div>
              <h3 class="text-sm font-semibold text-gray-800 truncate">{{ product.product_name }}</h3>
              <p class="text-xs text-gray-500 mt-1 truncate">{{ product.reason }}</p>
              <div class="flex items-center justify-between mt-3">
                <span class="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full font-medium">
                  {{ Math.round(product.confidence * 100) }}% match
                </span>
                <span class="text-xs text-primary-600 font-medium">View →</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="text-center py-8 text-gray-500">
          No recommendations yet. Visit the
          <NuxtLink :to="localePath('/pets')" class="text-primary-600 font-medium">pets page</NuxtLink>
          to get started.
        </div>
      </div>
    </section>

    <section v-if="hasFeature('show_categories_section') && visibleCategories.length > 0" class="py-12">
      <div class="max-w-6xl mx-auto px-4">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ t('home.categories') || 'Shop by Category' }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <NuxtLink
            v-for="cat in visibleCategories"
            :key="cat.slug"
            :to="localePath({ path: '/products', query: { category: cat.slug } })"
            class="bg-white rounded-xl shadow-sm border p-6 text-center hover:shadow-md transition group"
          >
            <img
              v-if="cat.image"
              :src="cat.image"
              class="w-16 h-16 mx-auto rounded-lg object-cover mb-3"
            />
            <div v-else class="text-4xl mb-3">{{ cat.icon }}</div>
            <h3 class="text-sm font-semibold text-gray-800 group-hover:text-primary-600 transition">
              {{ safeT(cat.nameKey, cat.name, cat.slug) }}
            </h3>
          </NuxtLink>
        </div>
      </div>
    </section>

    <section v-if="hasFeature('show_featured_products')" class="py-12 bg-gray-50">
      <div class="max-w-6xl mx-auto px-4">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ t('home.featured') || 'Featured Products' }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="prod in featuredProducts"
            :key="prod.id"
            class="bg-white rounded-xl shadow-sm border hover:shadow-md transition"
          >
            <NuxtLink :to="localePath(`/products/${prod.id}`)" class="block p-4">
              <div class="w-full h-32 bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg mb-3 flex items-center justify-center">
                <span class="text-4xl">{{ productIcon(prod.name) }}</span>
              </div>
              <h3 class="text-sm font-semibold text-gray-800 truncate">{{ prod.name }}</h3>
              <p class="text-xs text-gray-500 mt-1 line-clamp-1">{{ prod.description }}</p>
              <div class="flex items-center justify-between mt-3">
                <span class="text-sm font-bold text-primary-700">${{ prod.price }}</span>
                <span class="text-xs text-yellow-500">{{ '★'.repeat(Math.round(prod.rating || 0)) }}</span>
              </div>
            </NuxtLink>
          </div>
        </div>
      </div>
    </section>

    <section
      v-if="hasFeature('show_ai_teaser') && hasFeature('show_ai_chat')"
      class="py-12"
    >
      <div class="max-w-6xl mx-auto px-4">
        <div class="bg-gradient-to-r from-primary-50 to-primary-100 rounded-2xl p-8 text-center">
          <h2 class="text-2xl font-bold text-gray-900 mb-3">{{ t('home.aiTeaser') || 'AI-Powered Recommendations' }}</h2>
          <p class="text-gray-600 mb-6 max-w-xl mx-auto">
            {{ t('home.aiTeaserDesc') || 'Tell us about your pet and our AI will recommend the perfect products for their breed, age, and health needs.' }}
          </p>
          <NuxtLink
            :to="localePath('/chat')"
            class="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-semibold"
          >
            {{ t('home.startChat') || 'Start AI Chat' }}
          </NuxtLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { usePetStore } from '~/stores/pet'
import { useAuthStore } from '~/stores/auth'
import { useApi } from '~/composables/useApi'
import { useSiteProfile } from '~/composables/useSiteProfile'

const localePath = useLocalePath()
const petStore = usePetStore()
const { fetchPetRecommendations, fetchProducts } = useApi()
const { t, te } = useI18n()
const { profile, hasFeature, visibleCategories } = useSiteProfile()

// t(missingKey) 返回自身字符串（truthy），|| 回退失效，需先 te() 判断 key 是否存在
function safeT(key: string | undefined, ...fallbacks: (string | undefined)[]): string {
  if (key && te(key)) return t(key)
  for (const f of fallbacks) if (f) return f
  return ''
}

useHead({
  title: 'Home',
})

const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)

// ---------- Carousel ----------
const activeIndex = ref(0)
let autoplayTimer: ReturnType<typeof setInterval> | null = null

const maxIndex = computed(() => {
  const images = profile.value.homeHero.carousel.images
  return Math.max(0, images.length - 1)
})

function nextSlide() {
  if (maxIndex.value === 0) return
  activeIndex.value = activeIndex.value >= maxIndex.value ? 0 : activeIndex.value + 1
}

function prevSlide() {
  if (maxIndex.value === 0) return
  activeIndex.value = activeIndex.value <= 0 ? maxIndex.value : activeIndex.value - 1
}

function goToSlide(idx: number) {
  activeIndex.value = Math.max(0, Math.min(maxIndex.value, idx))
}

function startAutoplay() {
  if (autoplayTimer) return
  const { autoplay, interval } = profile.value.homeHero.carousel
  if (!autoplay || maxIndex.value === 0) return
  autoplayTimer = setInterval(() => {
    nextSlide()
  }, interval || 4000)
}

function stopAutoplay() {
  if (autoplayTimer) {
    clearInterval(autoplayTimer)
    autoplayTimer = null
  }
}

// ---------- Hero ----------
const heroBackgroundStyle = computed(() => {
  const bg = profile.value.homeHero.hero.backgroundImage
  if (bg) {
    return { backgroundImage: `url(${bg})`, backgroundSize: 'cover', backgroundPosition: 'center' }
  }
  return {}
})

const heroSectionCls = computed(() => {
  if (profile.value.homeHero.hero.backgroundImage) {
    return ''
  }
  return 'bg-gradient-to-br from-primary-600 to-primary-800'
})

const title = computed(() => {
  const h = profile.value.homeHero.hero
  return safeT(h.titleKey, h.title, safeT('hero.title', 'Smart Shopping for Your Pet'))
})

const subtitle = computed(() => {
  const h = profile.value.homeHero.hero
  return safeT(
    h.subtitleKey,
    h.subtitle,
    safeT(
      'hero.subtitle',
      "AI-powered product recommendations tailored to your pet's breed, age, and health needs. Discover the best food, toys, and accessories.",
    ),
  )
})

const cta1 = computed(() => {
  const h = profile.value.homeHero.hero
  return safeT(h.cta1LabelKey, h.cta1Label, safeT('hero.cta1Label', 'Shop Now'))
})

const cta1To = computed(() => {
  return profile.value.homeHero.hero.cta1To || '/products'
})

const cta2 = computed(() => {
  const h = profile.value.homeHero.hero
  return safeT(h.cta2LabelKey, h.cta2Label, safeT('hero.cta2Label', 'Add Your Pet'))
})

const cta2To = computed(() => {
  return profile.value.homeHero.hero.cta2To || '/pets'
})

// ---------- Data ----------
const featuredProducts = ref<any[]>([])
const tailoredProducts = ref<any[]>([])
const recLoading = ref(false)

function productIcon(name: string): string {
  const nameLower = name?.toLowerCase() || ''
  if (nameLower.includes('food') || nameLower.includes('kibble') || nameLower.includes('treat')) return '🍖'
  if (nameLower.includes('toy') || nameLower.includes('ball') || nameLower.includes('chew')) return '🎾'
  if (nameLower.includes('bed') || nameLower.includes('crate')) return '🛏️'
  if (nameLower.includes('collar') || nameLower.includes('leash') || nameLower.includes('harness')) return '🦮'
  if (nameLower.includes('shampoo') || nameLower.includes('brush') || nameLower.includes('groom')) return '✂️'
  if (nameLower.includes('health') || nameLower.includes('vitamin') || nameLower.includes('supplement')) return '💊'
  if (nameLower.includes('litter') || nameLower.includes('pad') || nameLower.includes('potty')) return '🧹'
  return '📦'
}

async function loadTailoredRecs() {
  if (!isLoggedIn.value || petStore.pets.length === 0) return

  recLoading.value = true
  try {
    const firstPet = petStore.pets[0]
    const result: any = await fetchPetRecommendations(firstPet.id)
    const recs = Array.isArray(result) ? result : (result?.items || [])
    tailoredProducts.value = recs.slice(0, 4)
  } catch {
    tailoredProducts.value = []
  } finally {
    recLoading.value = false
  }
}

onMounted(async () => {
  petStore.loadPets()

  try {
    const result: any = await fetchProducts({ limit: 4 })
    featuredProducts.value = Array.isArray(result) ? result : (result?.items || [])
  } catch {
    featuredProducts.value = []
  }

  await loadTailoredRecs()

  startAutoplay()
})

onUnmounted(() => {
  stopAutoplay()
})
</script>
