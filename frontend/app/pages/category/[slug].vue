<template>
  <div>
    <!-- DIY 装修分类页 -->
    <DiyPageRenderer
      v-if="diyComponents.length > 0"
      :components="diyComponents"
      :pending="diyPending"
      :error="!!diyError"
      @retry="refreshDiy"
    />

    <!-- 降级：硬编码分类页 -->
    <div v-else class="max-w-6xl mx-auto px-4 py-8">
      <!-- 分类标题 -->
      <div class="mb-8">
        <nav class="text-sm text-gray-500 mb-4">
          <NuxtLink to="/" class="hover:text-primary-600">{{ $t('common.home') }}</NuxtLink>
          <span class="mx-2">/</span>
          <span class="text-gray-900">{{ categoryName }}</span>
        </nav>
        <h1 class="text-2xl font-bold text-gray-900">{{ categoryName }}</h1>
      </div>

      <!-- Product Grid Fallback -->
      <div v-if="pending" class="text-center py-16">
        <div class="animate-spin w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full mx-auto" />
      </div>
      <div
        v-else-if="products.length > 0"
        class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
      >
        <NuxtLink
          v-for="p in products"
          :key="p.id"
          :to="`/products/${p.id}`"
          class="bg-white rounded-xl shadow-sm border hover:shadow-md transition p-4"
        >
          <div class="w-full h-32 bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg mb-3 flex items-center justify-center">
            <span class="text-4xl">{{ productIcon(p.name) }}</span>
          </div>
          <h3 class="text-sm font-semibold text-gray-800 truncate">{{ p.name }}</h3>
          <p class="text-sm font-bold text-primary-700 mt-2">${{ p.price }}</p>
        </NuxtLink>
      </div>
      <div v-else class="text-center py-16 text-gray-400">
        {{ $t('common.noResults') || 'No products found' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const route = useRoute()
const runtimeConfig = useRuntimeConfig()
const slug = computed(() => route.params.slug as string)

const categoryName = computed(() => {
  try {
    return decodeURIComponent(slug.value)
  } catch {
    return slug.value
  }
})

// --- DIY category page ---
const diyUrl = computed(() => `/api/v1/diy/by-type/category?slug=${slug.value}`)

const {
  data: diyPage,
  pending: diyPending,
  error: diyError,
  refresh: refreshDiy,
} = await useFetch(diyUrl, {
  baseURL: runtimeConfig.public.apiBase,
  server: false,
  default: () => null,
})

const diyComponents = computed<any[]>(() => (diyPage.value as any)?.components || [])

useHead({
  title: computed(() => (diyPage.value as any)?.title || categoryName.value),
  meta: [
    {
      name: 'description',
      content: computed(() => (diyPage.value as any)?.description || `Browse ${categoryName.value} products`),
    },
  ],
})

// --- Fallback products ---
const products = ref<any[]>([])
const pending = ref(true)

onMounted(async () => {
  try {
    const res = await useFetch(`/api/v1/products?category=${slug.value}`, {
      baseURL: runtimeConfig.public.apiBase,
      server: false,
    })
    products.value = (res.data.value as any)?.items || []
  } catch {
    products.value = []
  } finally {
    pending.value = false
  }
})

function productIcon(name: string): string {
  const n = name?.toLowerCase() || ''
  if (n.includes('food') || n.includes('kibble')) return '🍖'
  if (n.includes('toy') || n.includes('ball') || n.includes('chew')) return '🎾'
  if (n.includes('bed') || n.includes('crate')) return '🛏️'
  if (n.includes('collar') || n.includes('leash') || n.includes('harness')) return '🦮'
  if (n.includes('health') || n.includes('vitamin')) return '💊'
  return '📦'
}
</script>
