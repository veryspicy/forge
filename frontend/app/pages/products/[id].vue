<!-- Forge -- Product Detail Page -->
<template>
  <div>
    <!-- Breadcrumb -->
    <nav class="text-sm text-gray-500 mb-6">
      <NuxtLink :to="localePath('/')" class="hover:text-primary-600">{{ $t('common.home') }}</NuxtLink>
      <span class="mx-2">/</span>
      <NuxtLink :to="localePath('/products')" class="hover:text-primary-600">{{ $t('common.products') }}</NuxtLink>
      <span class="mx-2">/</span>
      <span class="text-gray-900 truncate">{{ product?.name || '...' }}</span>
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
              :alt="product.name"
              class="w-full h-full object-cover"
            />
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
              <img :src="img" :alt="`${product.name} - ${idx + 1}`" class="w-full h-full object-cover" />
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

          <h1 class="text-3xl font-bold text-gray-900">{{ product.name }}</h1>

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

          <!-- Description -->
          <p class="mt-5 text-gray-600 leading-relaxed">{{ product.description }}</p>

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
                {{ v.name }}
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
              :disabled="!isInStock"
              @click="addToCart"
            >
              {{ $t('products.addToCart') }}
            </button>
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
          <details class="mt-6 group" v-if="productSpecs.length > 0">
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
import { useCurrency } from '~/composables/useCurrency'
import ProductCard from '~/components/products/ProductCard.vue'

const localePath = useLocalePath()

const route = useRoute()
const productStore = useProductStore()
const cartStore = useCartStore()
const { t } = useI18n()
const { formatPrice } = useCurrency()

const product = computed(() => productStore.currentProduct)
const activeImage = ref('')
const quantity = ref(1)
const selectedVariant = ref<string | null>(null)
const relatedProducts = ref<any[]>([])

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

function addToCart() {
  const p = product.value
  if (!p) return
  cartStore.addItem({
    product: { id: p.id, name: p.name, price: p.price, image: p.images?.[0] },
    quantity: quantity.value,
  })
  quantity.value = 1
}

watchEffect(() => {
  if (product.value?.images?.length) {
    activeImage.value = product.value.images[0]
  }
})

onMounted(async () => {
  if (route.params.id) {
    await productStore.loadProduct(route.params.id as string)
  }
  if (productStore.products.length === 0) {
    await productStore.loadProducts({ page_size: 4 } as any)
  }
  relatedProducts.value = productStore.products.filter(
    (p) => p.id !== route.params.id
  ).slice(0, 4)
})
</script>