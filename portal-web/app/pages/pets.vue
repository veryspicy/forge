<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold text-gray-900">{{ $t('pets.title') }}</h1>
      <button
        class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium"
        @click="showWizard = true"
      >
        {{ $t('pets.addPet') }}
      </button>
    </div>

    <!-- Pet Wizard -->
    <div v-if="showWizard" class="bg-white rounded-xl shadow-sm border p-6 mb-8">
      <!-- Wizard Steps -->
      <div class="flex items-center gap-2 mb-6">
        <div
          v-for="(step, idx) in wizardSteps"
          :key="idx"
          class="flex items-center gap-2"
        >
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
            :class="wizardStep >= idx ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'"
          >
            {{ idx + 1 }}
          </div>
          <span class="text-sm" :class="wizardStep >= idx ? 'text-gray-900 font-medium' : 'text-gray-400'">{{ step }}</span>
          <div v-if="idx < wizardSteps.length - 1" class="w-8 h-px bg-gray-300" />
        </div>
      </div>

      <!-- Step 1: Pet Type & Name -->
      <div v-if="wizardStep === 0" class="space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">{{ $t('pets.step1Title') }}</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <button
            v-for="type in petTypes"
            :key="type"
            class="p-4 rounded-lg border-2 transition text-center"
            :class="form.type === type ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'"
            @click="form.type = type"
          >
            <span class="text-2xl block mb-1">{{ typeIcon(type) }}</span>
            <span class="text-sm font-medium text-gray-700">{{ type }}</span>
          </button>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.petName') }}</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            :placeholder="$t('pets.petNamePlaceholder')"
          />
        </div>
      </div>

      <!-- Step 2: Breed -->
      <div v-if="wizardStep === 1" class="space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">{{ $t('pets.step2Title') }}</h3>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.breed') }}</label>
          <select
            v-model="form.breed"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">{{ $t('pets.selectBreed') || 'Select breed' }}</option>
            <option value="GOLDEN_RETRIEVER">Golden Retriever</option>
            <option value="FRENCH_BULLDOG">French Bulldog</option>
            <option value="LABRADOR">Labrador</option>
            <option value="GERMAN_SHEPHERD">German Shepherd</option>
            <option value="POODLE">Poodle</option>
            <option value="HUSKY">Husky</option>
            <option value="CORGI">Corgi</option>
            <option value="SHIBA_INU">Shiba Inu</option>
            <option value="SIAMESE">Siamese Cat</option>
            <option value="PERSIAN">Persian Cat</option>
            <option value="MAINE_COON">Maine Coon</option>
            <option value="RAGDOLL">Ragdoll</option>
            <option value="PARROT">Parrot</option>
            <option value="BUDGIE">Budgie</option>
            <option value="HAMSTER">Hamster</option>
            <option value="GUINEA_PIG">Guinea Pig</option>
            <option value="RABBIT">Rabbit</option>
            <option value="OTHER">Other (Custom)</option>
          </select>
          <input
            v-if="form.breed === 'OTHER'"
            v-model="form.breed_custom"
            type="text"
            class="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            placeholder="Enter custom breed name"
          />
        </div>
      </div>

      <!-- Step 3: Details -->
      <div v-if="wizardStep === 2" class="space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">{{ $t('pets.step3Title') }}</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.gender') }}</label>
            <select
              v-model="form.gender"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">{{ $t('pets.selectGender') }}</option>
              <option value="male">{{ $t('pets.male') }}</option>
              <option value="female">{{ $t('pets.female') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.weight') }} (kg)</label>
            <input
              v-model.number="form.weight"
              type="number"
              step="0.1"
              min="0"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              placeholder="0.0"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.age') }}</label>
            <div class="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-700">
              {{ computedAge !== null ? computedAge + ' ' + $t('pets.years') : '-' }}
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.birthday') }}</label>
            <input
              v-model="form.birthday"
              type="date"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>
      </div>

      <!-- Step 4: Confirm -->
      <div v-if="wizardStep === 3" class="space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">{{ $t('pets.step4Title') }}</h3>
        <div class="bg-gray-50 rounded-lg p-4 space-y-2">
          <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.petName') }}:</span><span>{{ form.name }}</span></div>
          <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.type') }}:</span><span>{{ form.type }}</span></div>
          <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.breed') }}:</span><span>{{ form.breed === 'OTHER' ? form.breed_custom : (form.breed || mapBreedForApi('', form.type)) }}</span></div>
          <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.gender') }}:</span><span>{{ form.gender || '-' }}</span></div>
          <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.weight') }}:</span><span>{{ form.weight ? form.weight + ' kg' : '-' }}</span></div>
        </div>
        <button
          class="w-full py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="saving"
          @click="savePet"
        >
          {{ saving ? 'Saving...' : $t('pets.savePet') }}
        </button>
      </div>

      <!-- Wizard Nav -->
      <div class="flex justify-between mt-6 pt-4 border-t">
        <button
          class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition"
          :disabled="wizardStep === 0"
          @click="wizardStep--"
        >
          {{ $t('pets.back') }}
        </button>
        <div class="flex gap-2">
          <button
            class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition"
            @click="showWizard = false"
          >
            {{ $t('pets.cancel') }}
          </button>
          <button
            v-if="wizardStep < 3"
            class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition text-sm font-medium"
            :disabled="!canProceed"
            @click="wizardStep++"
          >
            {{ $t('pets.next') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Pets Grid -->
    <div v-if="petStore.pets.length > 0" class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="pet in petStore.pets"
        :key="pet.id"
        class="bg-white rounded-xl shadow-sm border hover:shadow-md transition"
      >
        <!-- Pet Card -->
        <div class="p-6">
          <div class="flex items-start justify-between mb-4">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{{ pet.name }}</h3>
              <p class="text-sm text-gray-500">{{ petAge(pet.birthday) }}</p>
            </div>
            <span class="text-3xl">{{ breedIcon(pet.breed) }}</span>
          </div>
          <div class="space-y-2 text-sm text-gray-600">
            <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.breed') }}:</span><span>{{ pet.breed || '-' }}</span></div>
            <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.gender') }}:</span><span>{{ pet.gender || '-' }}</span></div>
            <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.weight') }}:</span><span>{{ pet.weight ? pet.weight + ' kg' : '-' }}</span></div>
            <div class="flex gap-2"><span class="font-medium text-gray-700">{{ $t('pets.lifecycle') }}:</span><span>{{ pet.lifecycle || '-' }}</span></div>
          </div>
          <div class="flex gap-2 mt-4 pt-4 border-t">
            <button
              class="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition"
              @click="confirmDelete(pet)"
            >
              {{ $t('pets.delete') }}
            </button>
          </div>
        </div>

        <!-- Recommendations Section -->
        <div class="border-t bg-gray-50 rounded-b-xl px-6 py-4">
          <h4 class="text-sm font-semibold text-gray-700 mb-3">Tailored for {{ pet.name }}</h4>

          <!-- Loading -->
          <div v-if="recLoading[pet.id]" class="text-center py-3">
            <div class="animate-pulse text-sm text-gray-400">Loading recommendations...</div>
          </div>

          <!-- Recommendations loaded -->
          <div v-else-if="petRecs[pet.id] && petRecs[pet.id].length > 0" class="space-y-2">
            <div
              v-for="rec in petRecs[pet.id].slice(0, 3)"
              :key="rec.product_id"
              class="flex items-center gap-3 p-2 bg-white rounded-lg border cursor-pointer hover:border-primary-300 transition"
              @click="navigateTo(localePath(`/products/${rec.product_id}`))"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800 truncate">{{ rec.product_name }}</p>
                <p class="text-xs text-gray-500 truncate">{{ rec.reason }}</p>
              </div>
              <span class="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full font-medium">
                {{ Math.round(rec.confidence * 100) }}%
              </span>
            </div>
          </div>

          <!-- No recommendations yet -->
          <div v-else>
            <button
              class="w-full px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium"
              @click="loadRecsForPet(pet.id)"
            >
              View recommendations
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!showWizard && petStore.pets.length === 0" class="text-center py-16">
      <div class="text-6xl mb-4">🐾</div>
      <h3 class="text-xl font-semibold text-gray-900 mb-2">{{ $t('pets.noPetsYet') }}</h3>
      <p class="text-gray-500">{{ $t('pets.noPetsHint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { usePetStore } from '~/stores/pet'
import { useApi } from '~/composables/useApi'

definePageMeta({
  middleware: 'auth',
})

const petStore = usePetStore()
const { t } = useI18n()
const { fetchPetRecommendations } = useApi()
const localePath = useLocalePath()

const showWizard = ref(false)
const wizardStep = ref(0)

// Per-pet recommendation state
const recLoading = ref<Record<string, boolean>>({})
const petRecs = ref<Record<string, any[]>>({})

const wizardSteps = computed(() => [
  t('pets.wizardStep1'),
  t('pets.wizardStep2'),
  t('pets.wizardStep3'),
  t('pets.wizardStep4'),
])

const petTypes = ['dog', 'cat', 'bird', 'fish', 'rabbit', 'hamster']

const form = reactive({
  name: '',
  type: 'dog',
  breed: '',
  breed_custom: '',
  gender: '',
  weight: null as number | null,
  birthday: '',
})

const computedAge = computed(() => {
  if (!form.birthday) return null
  const ageMs = Date.now() - new Date(form.birthday).getTime()
  return Math.floor(ageMs / (365.25 * 24 * 60 * 60 * 1000))
})

const canProceed = computed(() => {
  if (wizardStep.value === 0) return form.name.trim() && form.type
  return true
})

function typeIcon(type: string): string {
  const icons: Record<string, string> = { dog: '🐕', cat: '🐈', bird: '🐦', fish: '🐟', rabbit: '🐰', hamster: '🐹' }
  return icons[type] || '🐾'
}

function breedIcon(breed: string): string {
  const b = (breed || '').toLowerCase()
  if (b.includes('retriever') || b.includes('labrador') || b.includes('bulldog') || b.includes('shepherd') || b.includes('poodle') || b.includes('husky') || b.includes('corgi') || b.includes('shiba') || b.includes('dog')) return '🐕'
  if (b.includes('siamese') || b.includes('persian') || b.includes('maine') || b.includes('ragdoll') || b.includes('cat')) return '🐈'
  if (b.includes('parrot') || b.includes('budgie') || b.includes('bird')) return '🐦'
  if (b.includes('fish')) return '🐟'
  if (b.includes('rabbit')) return '🐰'
  if (b.includes('hamster') || b.includes('guinea')) return '🐹'
  return '🐾'
}

function petAge(birthday: string | null): string {
  if (!birthday) return ''
  const ageMs = Date.now() - new Date(birthday).getTime()
  const years = Math.floor(ageMs / (365.25 * 24 * 60 * 60 * 1000))
  return `${years} ${t('pets.years')}`
}

// Must match backend PetBreed enum values
const VALID_BREEDS = [
  'UNKNOWN',
  'GOLDEN_RETRIEVER', 'FRENCH_BULLDOG', 'LABRADOR', 'GERMAN_SHEPHERD',
  'POODLE', 'HUSKY', 'CORGI', 'SHIBA_INU',
  'SIAMESE', 'PERSIAN', 'MAINE_COON', 'RAGDOLL', 'BRITISH_SHORT_HAIR',
  'PARROT', 'HAMSTER', 'GUINEA_PIG', 'BUDGIE',
]

function mapBreedForApi(breed: string, _type: string): string {
  if (breed && breed.trim()) {
    const mapped = breed.trim().toUpperCase().replace(/ /g, '_')
    if (VALID_BREEDS.includes(mapped)) return mapped
  }
  return 'UNKNOWN'
}

const saving = ref(false)

async function savePet() {
  if (saving.value) return
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      breed: form.breed === 'OTHER' ? 'OTHER' : mapBreedForApi(form.breed, form.type),
      breed_custom: form.breed === 'OTHER' ? form.breed_custom : undefined,
      birthday: form.birthday || new Date().toISOString().split('T')[0],
      weight: form.weight ?? undefined,
      gender: form.gender ? form.gender.toUpperCase() : 'UNKNOWN',
      health_notes: [],
      allergies: [],
      spayed_neutered: false,
    }
    await petStore.addPet(payload)
    showWizard.value = false
    wizardStep.value = 0
    form.name = ''
    form.type = 'dog'
    form.breed = ''
    form.breed_custom = ''
    form.gender = ''
    form.weight = null
    form.birthday = ''
  } catch (err: any) {
    alert(err?.data?.detail || err?.message || 'Failed to save pet profile')
  } finally {
    saving.value = false
  }
}

function viewPet(pet: any) {
  navigateTo(`/pets/${pet.id}`)
}

async function confirmDelete(pet: any) {
  if (confirm(t('pets.confirmDelete', { name: pet.name }) as string)) {
    await petStore.removePet(pet.id)
  }
}

async function loadRecsForPet(petId: string) {
  recLoading.value[petId] = true
  try {
    const result: any = await fetchPetRecommendations(petId)
    petRecs.value[petId] = Array.isArray(result) ? result : (result?.items || [])
  } catch {
    petRecs.value[petId] = []
  } finally {
    recLoading.value[petId] = false
  }
}

onMounted(() => {
  petStore.loadPets()
})
</script>
