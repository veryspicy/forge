<template>
  <div class="space-y-6">
    <!-- Category Filter -->
    <div>
      <h3 class="text-sm font-semibold text-gray-900 mb-3">{{ $t('products.category') }}</h3>
      <div class="space-y-2">
        <label
          v-for="cat in categories"
          :key="cat.value"
          class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer hover:text-gray-900"
        >
          <input
            type="checkbox"
            :value="cat.value"
            :checked="selectedCategories.includes(cat.value)"
            class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            @change="toggleCategory(cat.value)"
          />
          {{ cat.label }}
        </label>
      </div>
    </div>

    <!-- Price Range -->
    <div>
      <h3 class="text-sm font-semibold text-gray-900 mb-3">{{ $t('products.priceRange') }}</h3>
      <div class="flex items-center gap-2">
        <input
          v-model.number="priceMin"
          type="number"
          min="0"
          class="w-20 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
          placeholder="$0"
        />
        <span class="text-gray-400">-</span>
        <input
          v-model.number="priceMax"
          type="number"
          min="0"
          class="w-20 px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
          placeholder="$999"
        />
      </div>
    </div>

    <!-- Rating Filter -->
    <div>
      <h3 class="text-sm font-semibold text-gray-900 mb-3">{{ $t('products.rating') }}</h3>
      <div class="space-y-2">
        <label
          v-for="r in ratings"
          :key="r"
          class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer hover:text-gray-900"
        >
          <input
            type="radio"
            name="rating"
            :value="r"
            :checked="selectedRating === r"
            class="text-primary-600 focus:ring-primary-500"
            @change="selectedRating = r; emitUpdate()"
          />
          {{ '★'.repeat(r) }} &amp; up
        </label>
      </div>
    </div>

    <!-- Clear -->
    <button
      class="text-sm text-primary-600 hover:text-primary-800 transition font-medium"
      @click="clearFilters"
    >
      {{ $t('products.clearFilters') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const { t } = useI18n()

const props = defineProps<{ modelValue: Record<string, any> }>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, any>] }>()

const categories = [
  { label: t('categories.food'), value: 'food' },
  { label: t('categories.toys'), value: 'toys' },
  { label: t('categories.health'), value: 'health' },
  { label: t('categories.grooming'), value: 'grooming' },
  { label: t('categories.accessories'), value: 'accessories' },
]

const ratings = [4, 3, 2]
const selectedCategories = ref<string[]>([])
const priceMin = ref<number | null>(null)
const priceMax = ref<number | null>(null)
const selectedRating = ref<number | null>(null)

function toggleCategory(cat: string) {
  const idx = selectedCategories.value.indexOf(cat)
  if (idx >= 0) selectedCategories.value.splice(idx, 1)
  else selectedCategories.value.push(cat)
  emitUpdate()
}

function emitUpdate() {
  const filters: Record<string, any> = {}
  if (selectedCategories.value.length > 0) filters.category = selectedCategories.value
  if (priceMin.value != null) filters.price_min = priceMin.value
  if (priceMax.value != null) filters.price_max = priceMax.value
  if (selectedRating.value != null) filters.rating = selectedRating.value
  emit('update:modelValue', filters)
}

function clearFilters() {
  selectedCategories.value = []
  priceMin.value = null
  priceMax.value = null
  selectedRating.value = null
  emit('update:modelValue', {})
}
</script>
