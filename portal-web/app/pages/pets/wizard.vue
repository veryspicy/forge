<template>
  <div class="min-h-screen bg-gray-50 py-8">
    <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Page Header -->
      <div class="mb-8">
        <button
          @click="navigateTo('/pets')"
          class="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          {{ $t('common.back') }}
        </button>
        <h1 class="text-3xl font-bold text-gray-900">{{ $t('pets.wizardTitle') }}</h1>
      </div>

      <!-- Step Indicator -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div
            v-for="(step, idx) in steps"
            :key="idx"
            class="flex items-center"
          >
            <div class="flex items-center">
              <div
                :class="[
                  'flex items-center justify-center w-10 h-10 rounded-full text-sm font-medium border-2',
                  currentStep > idx
                    ? 'bg-indigo-600 border-indigo-600 text-white'
                    : currentStep === idx
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-gray-300 text-gray-500'
                ]"
              >
                <svg v-if="currentStep > idx" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <span
                :class="[
                  'ml-3 text-sm font-medium',
                  currentStep >= idx ? 'text-gray-900' : 'text-gray-400'
                ]"
              >
                {{ $t(`pets.wizardStep${idx + 1}`) }}
              </span>
            </div>
            <div
              v-if="idx < steps.length - 1"
              :class="[
                'flex-1 mx-4 h-0.5',
                currentStep > idx ? 'bg-indigo-600' : 'bg-gray-300'
              ]"
            ></div>
          </div>
        </div>
      </div>

      <!-- Form Card -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <!-- Step 1: Basic Info -->
        <div v-show="currentStep === 0">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">{{ $t('pets.step1Title') }}</h2>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.petName') }} *</label>
              <input
                v-model="form.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                :placeholder="$t('pets.enterName')"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.species') }} *</label>
              <select
                v-model="form.species"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">{{ $t('pets.selectSpecies') }}</option>
                <option value="Dog">{{ $t('pets.speciesDog') }}</option>
                <option value="Cat">{{ $t('pets.speciesCat') }}</option>
                <option value="Bird">{{ $t('pets.speciesBird') }}</option>
                <option value="Fish">{{ $t('pets.speciesFish') }}</option>
                <option value="Small Pet">{{ $t('pets.speciesSmallPet') }}</option>
                <option value="Other">{{ $t('pets.speciesOther') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.breed') }}</label>
              <input
                v-model="form.breed"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                :placeholder="$t('pets.enterBreed')"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.gender') }}</label>
              <div class="flex space-x-4">
                <label class="inline-flex items-center">
                  <input
                    v-model="form.gender"
                    type="radio"
                    value="Male"
                    class="form-radio h-4 w-4 text-indigo-600"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ $t('pets.male') }}</span>
                </label>
                <label class="inline-flex items-center">
                  <input
                    v-model="form.gender"
                    type="radio"
                    value="Female"
                    class="form-radio h-4 w-4 text-indigo-600"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ $t('pets.female') }}</span>
                </label>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.birthdayOrAge') }}</label>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">{{ $t('pets.birthday') }}</label>
                  <input
                    v-model="form.birthday"
                    type="date"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">{{ $t('pets.orAge') }}</label>
                  <input
                    v-model.number="form.age"
                    type="number"
                    min="0"
                    max="50"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    :placeholder="$t('pets.years')"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Details -->
        <div v-show="currentStep === 1">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">{{ $t('pets.step2Title') }}</h2>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.weight') }}</label>
              <input
                v-model.number="form.weight"
                type="number"
                min="0"
                max="200"
                step="0.1"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                :placeholder="$t('pets.enterWeight')"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.foodPreference') }}</label>
              <select
                v-model="form.foodPreference"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">{{ $t('pets.selectPreference') }}</option>
                <option value="Dry">{{ $t('pets.foodDry') }}</option>
                <option value="Wet">{{ $t('pets.foodWet') }}</option>
                <option value="Raw">{{ $t('pets.foodRaw') }}</option>
                <option value="Mixed">{{ $t('pets.foodMixed') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('pets.allergies') }}</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="allergy in allergyOptions"
                  :key="allergy"
                  type="button"
                  @click="toggleAllergy(allergy)"
                  :class="[
                    'px-3 py-1 rounded-full text-sm font-medium border transition-colors',
                    form.allergies.includes(allergy)
                      ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                  ]"
                >
                  {{ allergy }}
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('pets.activityLevel') }}</label>
              <div class="flex items-center space-x-2">
                <input
                  v-model.number="form.activityLevel"
                  type="range"
                  min="1"
                  max="5"
                  class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <span class="text-sm font-medium text-gray-700 w-8 text-center">{{ form.activityLevel }}</span>
              </div>
              <div class="flex justify-between text-xs text-gray-400 mt-1">
                <span>{{ $t('pets.low') }}</span>
                <span>{{ $t('pets.high') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3: Goals -->
        <div v-show="currentStep === 2">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">{{ $t('pets.step3Title') }}</h2>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('pets.healthGoals') }}</label>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <label
                  v-for="goal in healthGoalOptions"
                  :key="goal"
                  class="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50"
                  :class="form.healthGoals.includes(goal) ? 'border-indigo-300 bg-indigo-50' : 'border-gray-300'"
                >
                  <input
                    :value="goal"
                    v-model="form.healthGoals"
                    type="checkbox"
                    class="form-checkbox h-4 w-4 text-indigo-600 rounded"
                  />
                  <span class="ml-3 text-sm text-gray-700">{{ goal }}</span>
                </label>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('pets.specialNeeds') }}</label>
              <textarea
                v-model="form.specialNeeds"
                rows="4"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                :placeholder="$t('pets.specialNeedsPlaceholder')"
              ></textarea>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation Buttons -->
      <div class="flex justify-between">
        <button
          v-if="currentStep > 0"
          @click="prevStep"
          class="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          {{ $t('common.previous') }}
        </button>
        <div v-else></div>

        <button
          v-if="currentStep < steps.length - 1"
          @click="nextStep"
          class="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          {{ $t('common.next') }}
        </button>
        <button
          v-else
          @click="submitForm"
          :disabled="submitting"
          class="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="submitting" class="inline-flex items-center">
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ $t('common.submitting') }}
          </span>
          <span v-else>{{ $t('common.submit') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { usePetStore } from '~/stores/pet'

definePageMeta({
  middleware: 'auth',
})

const petStore = usePetStore()
const currentStep = ref(0)
const submitting = ref(false)

const steps = [
  { key: 'step1' },
  { key: 'step2' },
  { key: 'step3' },
]

const allergyOptions = [
  'Chicken', 'Beef', 'Wheat', 'Corn', 'Soy', 'Dairy', 'Eggs', 'Fish', 'Rice', 'Lamb'
]

const healthGoalOptions = [
  'Weight Management',
  'Shiny Coat',
  'Dental Health',
  'Joint Health',
  'Digestive Health',
  'Allergy Relief',
  'Energy Boost',
]

const form = reactive({
  name: '',
  species: '',
  breed: '',
  gender: '',
  birthday: '',
  age: null as number | null,
  weight: null as number | null,
  foodPreference: '',
  allergies: [] as string[],
  activityLevel: 3,
  healthGoals: [] as string[],
  specialNeeds: '',
})

const toggleAllergy = (allergy: string) => {
  const idx = form.allergies.indexOf(allergy)
  if (idx > -1) {
    form.allergies.splice(idx, 1)
  } else {
    form.allergies.push(allergy)
  }
}

const nextStep = () => {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function mapBreedForApi(breed: string, species: string): string {
  if (breed && breed.trim()) return breed.trim().toUpperCase().replace(/ /g, '_')
  return species ? species.toUpperCase().replace(/ /g, '_') : 'UNKNOWN'
}

const submitForm = async () => {
  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      breed: mapBreedForApi(form.breed, form.species),
      birthday: form.birthday || new Date().toISOString().split('T')[0],
      weight: form.weight ?? undefined,
      gender: form.gender ? form.gender.toUpperCase() : 'UNKNOWN',
      spayed_neutered: false,
      health_notes: form.healthGoals.length > 0 ? form.healthGoals : [],
      allergies: form.allergies,
    }
    await petStore.addPet(payload)
    navigateTo('/pets')
  } catch (err: any) {
    console.error('Failed to create pet:', err)
  } finally {
    submitting.value = false
  }
}
</script>