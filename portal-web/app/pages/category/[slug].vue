<template>
  <div>
    <!-- 降级：硬编码分类页 -->
    <div class="max-w-6xl mx-auto px-4 py-8">
      <div class="mb-8">
        <nav class="text-sm text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 mb-4">
          <NuxtLink :to="localePath('/')" class="hover:text-accent-600">{{ $t('common.home') }}</NuxtLink>
          <span class="mx-2">/</span>
          <span class="text-neutral-900 dark:text-neutral-100">{{ categoryName }}</span>
        </nav>
        <h1 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{{ categoryName }}</h1>
      </div>

      <div v-if="pending" class="text-center py-16">
        <div class="animate-spin w-8 h-8 border-4 border-accent-200 border-t-accent-600 rounded-full mx-auto" />
      </div>
      <div
        v-else-if="products.length > 0"
        class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
      >
        <NuxtLink
          v-for="(p, idx) in products"
          :key="p.id"
          v-reveal="{ delay: Math.min(idx, 11) * 50 }"
          :to="localePath(`/products/${p.slug || p.id}`)"
          class="bg-white dark:bg-stone-900 rounded-xl shadow-sm border hover:shadow-md transition p-4"
        >
          <div class="w-full h-32 bg-gradient-to-br from-accent-50 to-accent-100 rounded-lg mb-3 flex items-center justify-center">
<!-- eslint-disable-next-line vue/no-v-html -->
            <span class="text-4xl" v-html="productIcon(p.name)" />
          </div>
          <h3 class="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{{ p.name }}</h3>
          <p class="text-sm font-bold text-accent-700 mt-2">${{ p.price }}</p>
        </NuxtLink>
      </div>
      <div v-else class="text-center py-16 text-neutral-400 dark:text-neutral-400">
        {{ $t('common.noResults') || 'No products found' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { productIcon } from '~/utils/iconSvgs'

const localePath = useLocalePath()

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

// --- DIY category page removed; use hardcoded category page ---

useHead({
  title: computed(() => categoryName.value),
  meta: [
    {
      name: 'description',
      content: computed(() => `Browse ${categoryName.value} products`),
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


</script>
