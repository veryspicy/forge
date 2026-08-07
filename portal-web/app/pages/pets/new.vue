<!-- Forge -- Add Pet Page -->
<template>
  <div class="max-w-lg mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">{{ $t('pets.addPet') }}</h1>
    <form @submit.prevent="submit" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700">{{ $t('pets.petName') }}</label>
        <input v-model="form.name" required class="mt-1 block w-full px-3 py-2 border rounded-lg text-sm" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">{{ $t('pets.breed') }}</label>
        <select v-model="form.breed" required class="mt-1 block w-full px-3 py-2 border rounded-lg text-sm">
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
          required
          placeholder="Enter custom breed name"
          class="mt-2 block w-full px-3 py-2 border rounded-lg text-sm"
        />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">{{ $t('pets.birthday') }}</label>
        <input v-model="form.birthday" type="date" required class="mt-1 block w-full px-3 py-2 border rounded-lg text-sm" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700">{{ $t('pets.weight') }}</label>
        <input v-model="form.weight" type="number" step="0.1" class="mt-1 block w-full px-3 py-2 border rounded-lg text-sm" />
      </div>
      <button type="submit" class="w-full px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700">{{ $t('pets.savePet') }}</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { usePetStore } from '~/stores/pet'

definePageMeta({
  middleware: 'auth',
})

const router = useRouter();
const petStore = usePetStore();
const form = ref({ name: "", breed: "GOLDEN_RETRIEVER", breed_custom: "", birthday: "", weight: null as number | null });
const submit = async () => {
  const payload = {
    name: form.value.name.trim(),
    breed: form.value.breed === 'OTHER' ? 'OTHER' : form.value.breed,
    breed_custom: form.value.breed === 'OTHER' ? form.value.breed_custom : undefined,
    birthday: form.value.birthday || new Date().toISOString().split('T')[0],
    weight: form.value.weight ?? undefined,
    gender: 'UNKNOWN',
    health_notes: [],
    allergies: [],
    spayed_neutered: false,
  }
  await petStore.addPet(payload);
  router.push("/pets");
};
</script>