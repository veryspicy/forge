<template>
  <div class="pet-detail">
    <button class="back-btn" @click="navigateTo('/pets')">
      ← {{ $t('pets.back') }}
    </button>

    <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>

    <div v-else-if="error" class="error">
      {{ error }}
      <button @click="fetchData">{{ $t('common.retry') }}</button>
    </div>

    <template v-else-if="pet">
      <h1>{{ pet.name }}</h1>

      <section class="info-grid">
        <div class="info-item">
          <span class="label">{{ $t('pets.species') }}</span>
          <span class="value">{{ speciesLabel }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('pets.breed') }}</span>
          <span class="value">{{ pet.breed ? pet.breed.replace(/_/g, ' ') : pet.breed_custom || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('pets.gender') }}</span>
          <span class="value">{{ pet.gender ? $t(`pets.${pet.gender}`) : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('pets.birthday') }}</span>
          <span class="value">{{ pet.birthday || '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('pets.weight') }}</span>
          <span class="value">{{ pet.weight !== null ? pet.weight + ' kg' : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('pets.lifecycle') }}</span>
          <span class="value">{{ lifecycleLabel }}</span>
        </div>
        <div class="info-item">
          <span class="label">{{ $t('pets.spayedNeutered') }}</span>
          <span class="value">{{ pet.spayed_neutered ? $t('common.yes') : $t('common.no') }}</span>
        </div>
      </section>

      <section v-if="pet.allergies && pet.allergies.length" class="detail-section">
        <h2>{{ $t('pets.allergies') }}</h2>
        <div class="tags">
          <span v-for="a in pet.allergies" :key="a" class="tag">{{ a }}</span>
        </div>
      </section>

      <section v-if="pet.health_notes && pet.health_notes.length" class="detail-section">
        <h2>{{ $t('pets.healthNotes') }}</h2>
        <div class="tags">
          <span v-for="n in pet.health_notes" :key="n" class="tag">{{ n }}</span>
        </div>
      </section>

      <section v-if="recommendations.length" class="detail-section">
        <h2>{{ $t('pets.recommendedProducts') }}</h2>
        <div class="rec-grid">
          <div
            v-for="rec in recommendations"
            :key="rec.product_id"
            class="rec-card"
            @click="navigateTo(`/products/${rec.product_id}`)"
          >
            <div class="rec-name">{{ rec.product_name }}</div>
            <div class="rec-reason">{{ rec.reason }}</div>
          </div>
        </div>
      </section>

      <div class="actions">
        <button class="btn-delete" @click="handleDelete">{{ $t('pets.delete') }}</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useApi } from '~/composables/useApi'

const route = useRoute()
const { fetchPet, fetchPetRecommendations, deletePet } = useApi()
const petStore = usePetStore()
const { t } = useI18n()

const pet = ref<any>(null)
const loading = ref(true)
const error = ref('')
const recommendations = ref<any[]>([])

const SPECIES_MAP: Record<string, string> = {
  dog: 'pets.speciesDog',
  cat: 'pets.speciesCat',
  bird: 'pets.speciesBird',
  fish: 'pets.speciesFish',
  small_pet: 'pets.speciesSmallPet',
  other: 'pets.speciesOther',
}

const speciesLabel = computed(() => {
  if (!pet.value?.breed) return '-'
  const key = SPECIES_MAP[pet.value.breed]
  return key ? t(key) : pet.value.breed
})

const lifecycleLabel = computed(() => {
  if (!pet.value?.lifecycle) return '-'
  return pet.value.lifecycle.replace(/_/g, ' ')
})

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id as string
    const [p, recs] = await Promise.all([
      fetchPet(id),
      fetchPetRecommendations(id),
    ])
    pet.value = p
    recommendations.value = Array.isArray(recs) ? recs : ((recs as any)?.items || [])
  } catch (err: any) {
    error.value = err?.data?.detail || err?.message || t('pets.notFound')
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (confirm(t('pets.confirmDelete', { name: pet.value?.name }) as string)) {
    await deletePet(pet.value.id)
    navigateTo('/pets')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.pet-detail {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.back-btn {
  background: none;
  border: none;
  color: #555;
  cursor: pointer;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  padding: 0;
}

.back-btn:hover {
  color: #111;
}

h1 {
  font-size: 1.8rem;
  margin-bottom: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.info-item {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 0.75rem 1rem;
}

.label {
  display: block;
  font-size: 0.8rem;
  color: #888;
  margin-bottom: 0.25rem;
}

.value {
  font-size: 1rem;
  font-weight: 500;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h2 {
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  background: #e8f0fe;
  color: #1a73e8;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
}

.rec-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 0.75rem;
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.rec-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.rec-name {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.rec-reason {
  font-size: 0.85rem;
  color: #666;
}

.actions {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #eee;
}

.btn-delete {
  background: #dc2626;
  color: #fff;
  border: none;
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  cursor: pointer;
}

.btn-delete:hover {
  background: #b91c1c;
}

.loading,
.error {
  text-align: center;
  padding: 3rem 0;
  color: #888;
}

.error button {
  display: block;
  margin: 0.75rem auto 0;
  padding: 0.4rem 1rem;
}
</style>
