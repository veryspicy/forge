<!-- Forge -- Product Detail Page -->
<template>
  <div>
    <!-- Breadcrumb -->
    <nav class="max-w-6xl mx-auto text-sm text-gray-500 mb-6">
      <NuxtLink :to="localePath('/')" class="hover:text-primary-600">{{ $t('common.home') }}</NuxtLink>
      <span class="mx-2">/</span>
      <NuxtLink :to="localePath('/products')" class="hover:text-primary-600">{{ $t('common.products') }}</NuxtLink>
      <span class="mx-2">/</span>
      <span class="text-gray-900 truncate">{{ displayName }}</span>
    </nav>

    <!-- Loading -->
    <div v-if="productStore.loading" class="text-center py-20">
      <div class="animate-spin w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full mx-auto" />
      <p class="mt-4 text-gray-500">{{ $t('products.loadingProduct') }}</p>
    </div>

    <!-- Error -->
    <div v-else-if="!product" class="text-center py-20">
      <p class="text-gray-500 text-lg">{{ $t('products.notFound') }}</p>
      <NuxtLink :to="localePath('/products')" class="mt-4 text-primary-600 hover:underline inline-block">{{ $t('products.backToProducts') }}</NuxtLink>
    </div>

    <!-- Product Detail -->
    <div v-else class="max-w-6xl mx-auto">
      <div class="grid md:grid-cols-2 gap-8 lg:gap-12">
        <!-- Image Gallery -->
        <div>
          <!-- Main Image -->
          <div class="bg-gray-100 rounded-xl overflow-hidden h-80 md:h-96 flex items-center justify-center">
            <img
              v-if="activeImage"
              :src="activeImage"
              :alt="activeImageAlt"
              class="w-full h-full object-cover"
            >
            <span v-else class="text-gray-400">{{ $t('products.noImage') }}</span>
          </div>

          <!-- Thumbnails -->
          <div v-if="(product.images && product.images.length > 1)" class="flex gap-2 mt-3">
            <button
              v-for="(img, idx) in product.images"
              :key="idx"
              class="w-16 h-16 rounded-lg border-2 overflow-hidden transition flex-shrink-0"
              :class="activeImage === img ? 'border-primary-500' : 'border-gray-200 hover:border-gray-400'"
              @click="activeImage = img"
            >
              <img :src="img" :alt="imageAlt(img, idx)" class="w-full h-full object-cover" >
            </button>
          </div>
        </div>

        <!-- Product Info -->
        <div>
          <!-- AI Recommended Badge -->
          <span
            v-if="product.is_ai_generated || product.tags?.includes('ai-recommended')"
            class="inline-block bg-secondary-500 text-white text-xs font-medium px-3 py-1 rounded-full mb-3"
          >
            {{ $t('products.aiRecommended') }}
          </span>

          <h1 class="text-3xl font-bold text-gray-900">{{ displayName }}</h1>

          <!-- SKU -->
          <p v-if="product.sku" class="text-sm text-gray-400 mt-1">SKU: {{ product.sku }}</p>

          <!-- Rating -->
          <div class="flex items-center gap-2 mt-3">
            <span class="text-secondary-400 text-lg">
              {{ '★'.repeat(Math.floor(product.rating || 0)) }}
            </span>
            <span class="text-gray-300 text-lg">
              {{ '☆'.repeat(5 - Math.floor(product.rating || 0)) }}
            </span>
            <span class="text-sm text-gray-500">({{ product.review_count || 0 }} {{ $t('products.reviews') }})</span>
          </div>

          <!-- Price -->
          <div class="mt-4 flex items-baseline gap-3">
            <span class="text-3xl font-bold text-primary-600">
              {{ formatPrice(product.price) }}
            </span>
            <span v-if="product.original_price && product.original_price > product.price" class="text-lg text-gray-400 line-through">
              {{ formatPrice(product.original_price) }}
            </span>
          </div>

          <!-- Inventory Status -->
          <div class="flex items-center gap-2 mt-3">
            <span
              class="w-2.5 h-2.5 rounded-full"
              :class="inventoryClass"
            />
            <span class="text-sm font-medium">{{ inventoryLabel }}</span>
          </div>

          <!-- Description (localized) -->
          <p v-if="displayDescription" class="mt-5 text-gray-600 leading-relaxed">{{ displayDescription }}</p>

          <!-- Variants -->
          <div v-if="product.variants && product.variants.length > 0" class="mt-5">
            <p class="text-sm font-medium text-gray-700 mb-2">{{ $t('products.options') }}:</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="v in product.variants"
                :key="v.id"
                class="px-4 py-2 border rounded-lg text-sm transition"
                :class="selectedVariant === v.id
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'"
                @click="selectedVariant = v.id"
              >
                {{ variantDisplayName(v) }}
              </button>
            </div>
          </div>

          <!-- Quantity & Add to Cart -->
          <div class="mt-6 flex items-center gap-4">
            <div class="flex items-center border rounded-lg">
              <button
                class="px-3 py-2 text-gray-500 hover:text-gray-700 disabled:opacity-30"
                :disabled="quantity <= 1"
                @click="quantity--"
              >
                -
              </button>
              <span class="px-4 py-2 font-medium text-gray-900 select-none">{{ quantity }}</span>
              <button
                class="px-3 py-2 text-gray-500 hover:text-gray-700"
                :disabled="!isInStock"
                @click="quantity++"
              >
                +
              </button>
            </div>
            <button
              class="flex-1 px-6 py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!isInStock || adding"
              @click="addToCart"
            >
              {{ $t('products.addToCart') }}
            </button>
          </div>

          <!-- Trust Badges -->
          <div class="mt-6 grid grid-cols-3 gap-2 text-center">
            <div class="flex flex-col items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-2.5">
              <svg class="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h8m-8 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm8 0a2 2 0 1 0 4 0 2 2 0 0 0-4 0zm-8 3v6m8-6v6m-10 0h12a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2z" />
              </svg>
              <span class="text-xs font-medium text-gray-700">{{ $t('products.trustFreeShipping') }}</span>
            </div>
            <div class="flex flex-col items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-2.5">
              <svg class="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v6h6M20 20v-6h-6M4 16a8 8 0 0 0 14.1 2.5M20 8A8 8 0 0 0 5.9 5.5" />
              </svg>
              <span class="text-xs font-medium text-gray-700">{{ $t('products.trustReturns') }}</span>
            </div>
            <div class="flex flex-col items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-2.5">
              <svg class="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm7-3a7 7 0 1 1-14 0 7 7 0 0 1 14 0z" />
              </svg>
              <span class="text-xs font-medium text-gray-700">{{ $t('products.trustSecure') }}</span>
            </div>
          </div>

          <!-- Pet Suitability Tags -->
          <div v-if="product.breed_groups && product.breed_groups.length > 0" class="mt-5">
            <p class="text-sm font-medium text-gray-700 mb-2">{{ $t('products.suitableFor') }}:</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="bg in product.breed_groups"
                :key="bg"
                class="px-3 py-1 bg-primary-50 text-primary-700 text-xs rounded-full border border-primary-200"
              >
                {{ bg }}
              </span>
            </div>
          </div>

          <!-- Specifications (Collapsible) -->
          <details v-if="productSpecs.length > 0" class="mt-6 group">
            <summary class="text-sm font-medium text-gray-700 cursor-pointer list-none flex items-center gap-1">
              {{ $t('products.specifications') }}
              <span class="transition-transform group-open:rotate-90">&#9654;</span>
            </summary>
            <table class="mt-3 w-full text-sm border-collapse">
              <tbody>
                <tr v-for="spec in productSpecs" :key="spec.label" class="border-b border-gray-100">
                  <td class="py-2 pr-4 text-gray-500 font-medium">{{ $t(`products.spec.${spec.label.toLowerCase()}`) }}</td>
                  <td class="py-2 text-gray-900">{{ spec.value }}</td>
                </tr>
              </tbody>
            </table>
          </details>
        </div>
      </div>

      <!-- Structured Detail Blocks -->
      <section v-if="detailBlocks.length" class="mt-16">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ $t('products.detailsTitle') }}</h2>
        <DetailBlocks :blocks="detailBlocks" />
      </section>

      <!-- Customer Reviews -->
      <section class="mt-16">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ $t('reviews.productTitle') }}</h2>
        <div v-if="reviewsLoading" class="text-sm text-gray-500 py-4">{{ $t('common.loading') }}</div>
        <template v-else-if="productReviews.length > 0">
          <div v-if="reviewSummary" class="flex items-center gap-4 bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
            <div class="text-center">
              <div class="text-3xl font-bold text-gray-900">{{ reviewSummary.average_rating }}</div>
              <div class="text-yellow-400 text-sm mt-1">
                <span v-for="s in 5" :key="s" :class="s <= Math.round(reviewSummary.average_rating) ? '' : 'opacity-30'">★</span>
              </div>
            </div>
            <div class="text-sm text-gray-600">
              <p>{{ $t('reviews.avgLabel') }} · {{ $t('reviews.totalLabel', { count: reviewSummary.review_count }) }}</p>
              <div class="mt-2 space-y-1">
                <div
                  v-for="star in [5, 4, 3, 2, 1]"
                  :key="star"
                  class="flex items-center gap-2"
                >
                  <span class="w-8 text-gray-500">{{ star }}★</span>
                  <div class="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
                    <div
                      class="h-full bg-yellow-400"
                      :style="{ width: (reviewSummary.review_count ? (reviewSummary.distribution?.[star] || 0) / reviewSummary.review_count * 100 : 0) + '%' }"
                    />
                  </div>
                  <span class="w-6 text-xs text-gray-400 text-right">{{ reviewSummary.distribution?.[star] || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
          <ul class="space-y-4">
            <li
              v-for="rv in productReviews"
              :key="rv.id"
              class="border border-gray-200 rounded-lg p-4"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="text-yellow-400 text-sm">
                  <span v-for="s in 5" :key="s" :class="s <= rv.rating ? '' : 'opacity-30'">★</span>
                </div>
                <span class="text-xs text-gray-400">{{ formatReviewDate(rv.created_at) }}</span>
              </div>
              <p v-if="rv.title" class="font-medium text-gray-900">{{ rv.title }}</p>
              <p v-if="rv.content" class="text-sm text-gray-600 mt-1">{{ rv.content }}</p>
            </li>
          </ul>
        </template>
        <div v-else class="border border-dashed border-gray-300 rounded-lg p-8 text-center text-sm text-gray-500">
          {{ $t('reviews.empty') }}
        </div>
      </section>

      <!-- Related Products -->
      <section v-if="relatedProducts.length > 0" class="mt-16">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">{{ $t('products.relatedTitle') }}</h2>
        <div class="flex gap-6 overflow-x-auto pb-4 scrollbar-hide">
          <div
            v-for="rp in relatedProducts"
            :key="rp.id"
            class="min-w-[240px] max-w-[240px] flex-shrink-0"
          >
            <ProductCard :product="rp" />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useProductStore } from '~/stores/product'
import { useCartStore } from '~/stores/cart'
import { useAuthStore } from '~/stores/auth'
import { useCurrency } from '~/composables/useCurrency'
import { useApi } from '~/composables/useApi'
import { useToast } from '~/composables/useToast'
import ProductCard from '~/components/products/ProductCard.vue'
import DetailBlocks from '~/components/products/DetailBlocks.vue'

const localePath = useLocalePath()

const route = useRoute()
const productStore = useProductStore()
const cartStore = useCartStore()
const { fetchProductReviews } = useApi()
const { t, locale } = useI18n()
const { formatPrice } = useCurrency()
const { toast } = useToast()
const authStore = useAuthStore()

const product = computed(() => productStore.currentProduct)
const activeImage = ref('')
const quantity = ref(1)
const adding = ref(false)
const selectedVariant = ref<string | null>(null)
const relatedProducts = ref<any[]>([])
const productReviews = ref<any[]>([])
const reviewsLoading = ref(false)
const reviewSummary = ref<any>(null)

// 语言映射：C 端 locale(zh/en/ar/de/fr) → 后端翻译 key（zh-cn/es/de 等）
const backendLocaleKey = computed(() => {
  const l = locale.value
  if (l === 'zh') return 'zh-cn'
  return l
})

function localizedText(translations: Record<string, string> | undefined, fallback: string): string {
  if (!translations) return fallback || ''
  const key = backendLocaleKey.value
  if (translations[key]) return translations[key]
  if (translations[locale.value]) return translations[locale.value]
  if (translations.en) return translations.en
  return fallback || ''
}

function variantDisplayName(v: any): string {
  return localizedText(v?.name_translations, v?.name || '')
}

// SEO 多语言：seo_translations[locale] 逐级回退，未填则返回 undefined 走基准语言
function localizedSeo(seoKey: 'title' | 'description' | 'keywords'): string | string[] | undefined {
  const p = product.value
  const t = p?.seo_translations || {}
  const entry = t[backendLocaleKey.value] || t[locale.value] || t.en || {}
  const v = entry[seoKey]
  if (v === undefined || v === null || v === '') return undefined
  return v
}

const displayName = computed(() =>
  localizedText(product.value?.name_translations, product.value?.name || '')
)

const displayDescription = computed(() =>
  localizedText(product.value?.description_translations, product.value?.description || '')
)

const detailBlocks = computed(() => {
  const p = product.value
  if (!p) return []
  // 详情块多语言：优先当前 locale 的整组块，逐级回退到 en / 基准块（Shopify 字段级模型）
  const translations = p.detail_blocks_translations || {}
  const key = backendLocaleKey.value
  if (translations[key]?.length) return translations[key]
  if (translations[locale.value]?.length) return translations[locale.value]
  if (translations.en?.length) return translations.en
  return p.detail_blocks || []
})

// 图片 alt：当前语种翻译 → 基准 alt → 商品名（SEO/无障碍）
function imageAlt(img: string, idx: number): string {
  const detail = product.value?.image_details?.find((d) => d.url === img)
  const tr = detail?.alt_translations || {}
  return (
    tr[backendLocaleKey.value] ||
    tr[locale.value] ||
    tr.en ||
    detail?.alt ||
    `${displayName.value} - ${idx + 1}`
  )
}

const activeImageAlt = computed(() => {
  if (!product.value || !activeImage.value) return displayName.value
  return imageAlt(activeImage.value, 0)
})

// SEO：seo_translations[locale] 优先，回退基准 seo_*；JSON-LD Product schema
useSeoMeta({
  title: () => (localizedSeo('title') as string | undefined) || product.value?.seo_title || displayName.value,
  description: () => (localizedSeo('description') as string | undefined) || product.value?.seo_description || displayDescription.value,
  keywords: () => {
    const kws = (localizedSeo('keywords') as string[] | undefined) || product.value?.seo_keywords || undefined
    if (!kws) return undefined
    return Array.isArray(kws) ? kws.join(', ') : kws
  },
  ogTitle: () => displayName.value,
  ogDescription: () => displayDescription.value,
  ogImage: () => product.value?.main_image || product.value?.images?.[0] || undefined,
})

useHead(() => {
  const p = product.value
  if (!p) return {}
  return {
    script: [
      {
        type: 'application/ld+json',
        innerHTML: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'Product',
          name: displayName.value,
          sku: p.sku,
          description: displayDescription.value,
          image: p.main_image ? [p.main_image] : (p.images || []),
          offers: {
            '@type': 'Offer',
            price: p.price,
            priceCurrency: 'USD',
            availability: (p.inventory ?? 0) > 0 ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
          },
          ...(p.rating ? { aggregateRating: { '@type': 'AggregateRating', ratingValue: p.rating, reviewCount: p.review_count || 0 } } : {}),
        }),
      },
    ],
  }
})

function formatReviewDate(value: string | null) {
  if (!value) return ''
  return new Date(value).toLocaleDateString()
}

const isInStock = computed(() => {
  const inv = product.value?.inventory
  return inv == null || inv > 0
})

const inventoryClass = computed(() => {
  const inv = product.value?.inventory
  if (inv == null) return 'bg-gray-300'
  if (inv <= 0) return 'bg-red-500'
  if (inv <= 5) return 'bg-yellow-500'
  return 'bg-green-500'
})

const inventoryLabel = computed(() => {
  const inv = product.value?.inventory
  if (inv == null) return t('products.inStock')
  if (inv <= 0) return t('products.outOfStock')
  if (inv <= 5) return `${t('products.lowStock')} - ${t('products.onlyLeft', { count: inv })}`
  return t('products.inStock')
})

const productSpecs = computed(() => {
  const p = product.value
  if (!p) return []
  const specs: { label: string; value: string }[] = []
  if (p.weight) specs.push({ label: 'weight', value: p.weight })
  if (p.dimensions) specs.push({ label: 'dimensions', value: p.dimensions })
  if (p.material) specs.push({ label: 'material', value: p.material })
  if (p.ingredients) specs.push({ label: 'ingredients', value: p.ingredients })
  return specs
})

async function addToCart() {
  const p = product.value
  if (!p || adding.value) return
  adding.value = true
  try {
    await cartStore.addItem({
      product: {
        id: String(p.id),
        name: p.name,
        price: Number(p.price) || 0,
        image: p.images?.[0] || '',
      },
      quantity: quantity.value,
    })
    toast.success(t('products.addedToCart', { name: p.name }))
    quantity.value = 1
  } catch {
    // 未登录：明确提示并引导登录；其余失败给可重试提示，不再静默无响应
    if (!authStore.isAuthenticated) {
      toast.error(t('products.loginRequired'))
      navigateTo(localePath(`/login?redirect=${encodeURIComponent(route.fullPath)}`))
      return
    }
    toast.error(t('products.addToCartFailed'))
  } finally {
    adding.value = false
  }
}

watchEffect(() => {
  const images = product.value?.images
  if (images?.length) {
    const main = product.value?.main_image
    activeImage.value = main && images.includes(main) ? main : images[0]
  }
})

onMounted(async () => {
  if (route.params.slug) {
    await productStore.loadProduct(route.params.slug as string)
  }
  // 数字 ID 老链接自动重定向到 slug URL（SEO / 链接统一）
  const rawSlug = route.params.slug as string
  if (rawSlug && /^\d+$/.test(rawSlug) && product.value?.slug && String(product.value.slug) !== rawSlug) {
    await navigateTo(localePath(`/products/${product.value.slug}`), { replace: true })
    return
  }
  if (product.value) {
    reviewsLoading.value = true
    try {
      const res = await fetchProductReviews(product.value.id)
      productReviews.value = res?.items || []
      reviewSummary.value = res?.summary || null
    } catch {
      productReviews.value = []
      reviewSummary.value = null
    } finally {
      reviewsLoading.value = false
    }
  }
  if (productStore.products.length === 0) {
    await productStore.loadProducts({ page_size: 4 } as any)
  }
  relatedProducts.value = productStore.products.filter(
    (p) => String(p.id) !== String(product.value?.id)
  ).slice(0, 4)
})
</script>