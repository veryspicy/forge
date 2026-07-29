<template>
  <div>
    <!-- Hero Section -->
    <section class="hero bg-gradient-to-br from-primary-600 to-primary-800 text-white py-20">
      <div class="max-w-6xl mx-auto px-4 text-center">
        <h1 class="text-4xl md:text-5xl font-bold mb-4">
          {{ $t('home.heroTitle') || 'Smart Shopping for Your Pet' }}
        </h1>
        <p class="text-lg text-primary-100 mb-8 max-w-2xl mx-auto">
          {{ $t('home.heroDesc') || 'AI-powered product recommendations tailored to your pet\'s breed, age, and health needs. Discover the best food, toys, and accessories.' }}
        </p>
        <div class="flex justify-center gap-4">
          <NuxtLink to="/products" class="px-6 py-3 bg-white text-primary-700 rounded-lg hover:bg-gray-100 transition font-semibold">
            {{ $t('home.shopNow') || 'Shop Now' }}
          </NuxtLink>
          <NuxtLink to="/pets" class="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-400 transition font-semibold border border-primary-300">
            {{ $t('home.addPet') || 'Add Your Pet' }}
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- Tailored for Your Pet -->
    <section v-if="isLoggedIn && petStore.pets.length > 0" class="bg-gray-50 py-12">
      <div class="max-w-6xl mx-auto px-4">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900">
            Tailored for Your Pet
          </h2>
          <NuxtLink to="/chat" class="text-sm text-primary-600 hover:text-primary-700 font-medium">
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
            @click="navigateTo(`/products/${product.product_id}`)"
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
          <NuxtLink to="/pets" class="text-primary-600 font-medium">pets page</NuxtLink>
          to get started.
        </div>
      </div>
    </section>

    <!-- Categories -->
    <section class="py-12">
      <div class="max-w-6xl mx-auto px-4">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ $t('home.categories') || 'Shop by Category' }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <NuxtLink
            v-for="cat in categories"
            :key="cat.slug"
            :to="`/products?category=${cat.slug}`"
            class="bg-white rounded-xl shadow-sm border p-6 text-center hover:shadow-md transition group"
          >
            <div class="text-4xl mb-3">{{ cat.icon }}</div>
            <h3 class="text-sm font-semibold text-gray-800 group-hover:text-primary-600 transition">{{ cat.name }}</h3>
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- Featured Products -->
    <section class="py-12 bg-gray-50">
      <div class="max-w-6xl mx-auto px-4">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ $t('home.featured') || 'Featured Products' }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="prod in featuredProducts"
            :key="prod.id"
            class="bg-white rounded-xl shadow-sm border hover:shadow-md transition"
          >
            <NuxtLink :to="`/products/${prod.id}`" class="block p-4">
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

    <!-- AI Recommendation Teaser -->
    <section class="py-12">
      <div class="max-w-6xl mx-auto px-4">
        <div class="bg-gradient-to-r from-primary-50 to-primary-100 rounded-2xl p-8 text-center">
          <h2 class="text-2xl font-bold text-gray-900 mb-3">{{ $t('home.aiTeaser') || 'AI-Powered Recommendations' }}</h2>
          <p class="text-gray-600 mb-6 max-w-xl mx-auto">
            {{ $t('home.aiTeaserDesc') || 'Tell us about your pet and our AI will recommend the perfect products for their breed, age, and health needs.' }}
          </p>
          <NuxtLink
            to="/chat"
            class="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-semibold"
          >
            {{ $t('home.startChat') || 'Start AI Chat' }}
          </NuxtLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePetStore } from '~/stores/pet'
import { useAuthStore } from '~/stores/auth'
import { useApi } from '~/composables/useApi'

const petStore = usePetStore()
const { fetchPetRecommendations, fetchProducts } = useApi()
const { t } = useI18n()

// Simpler isLoggedIn check
const isLoggedIn = computed(() => {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null
  return !!token
})

const categories = computed(() => [
  { name: t('categories.food') || 'Food', slug: 'food', icon: '🍖' },
  { name: t('categories.toys') || 'Toys', slug: 'toys', icon: '🎾' },
  { name: t('categories.health') || 'Health', slug: 'health', icon: '💊' },
  { name: t('categories.accessories') || 'Accessories', slug: 'accessories', icon: '🎀' },
  { name: t('categories.grooming') || 'Grooming', slug: 'grooming', icon: '✂️' },
  { name: t('categories.training') || 'Training', slug: 'training', icon: '🦮' },
  { name: t('categories.furniture') || 'Furniture', slug: 'furniture', icon: '🛏️' },
  { name: t('categories.litter') || 'Litter', slug: 'litter', icon: '🧹' },
])

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

  // Load featured products for fallback display
  try {
    const result: any = await fetchProducts({ limit: 4 })
    featuredProducts.value = Array.isArray(result) ? result : (result?.items || [])
  } catch {
    featuredProducts.value = []
  }

  await loadTailoredRecs()
})
</script>
