// Forge — Pet Store
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

interface Pet {
  id: string;
  owner_id: string;
  name: string;
  breed: string;
  birthday: string | null;
  weight: number | null;
  gender: string;
  lifecycle: string;
  spayed_neutered: boolean;
  health_notes: string[];
  allergies: string[];
}

export const usePetStore = defineStore("pet", () => {
  const pets = ref<Pet[]>([]);
  const loading = ref(false);
  const currentPetId = ref<string | null>(null);
  const recommendations = ref<any[]>([]);

  const { fetchPets, createPet, updatePet, deletePet, fetchPetRecommendations } = useApi();

  const currentPet = computed(() => {
    if (!currentPetId.value) return null;
    return pets.value.find((p) => p.id === currentPetId.value) || null;
  });

  const loadPets = async () => {
    loading.value = true;
    try {
      pets.value = (await fetchPets()) as any;
    } catch {
      pets.value = [];
    } finally {
      loading.value = false;
    }
  };

  const addPet = async (data: any) => {
    const pet = await createPet(data);
    pets.value.push(pet as any);
    return pet;
  };

  const setCurrentPet = async (petId: string) => {
    currentPetId.value = petId;
    await loadRecommendations(petId);
  };

  const loadRecommendations = async (petId: string) => {
    try {
      const result: any = await fetchPetRecommendations(petId);
      recommendations.value = result.items || result || [];
    } catch {
      recommendations.value = [];
    }
  };

  const removePet = async (petId: string) => {
    try {
      await deletePet(petId);
      pets.value = pets.value.filter((p) => p.id !== petId);
      if (currentPetId.value === petId) {
        currentPetId.value = null;
        recommendations.value = [];
      }
    } catch (error) {
      throw error;
    }
  };

  const editPet = async (petId: string, data: Partial<Pet>) => {
    try {
      const updated = (await updatePet(petId, data)) as any;
      const idx = pets.value.findIndex((p) => p.id === petId);
      if (idx !== -1) {
        pets.value[idx] = { ...pets.value[idx], ...updated };
      }
      return updated;
    } catch (error) {
      throw error;
    }
  };

  return {
    pets,
    loading,
    currentPetId,
    currentPet,
    recommendations,
    loadPets,
    addPet,
    setCurrentPet,
    loadRecommendations,
    removePet,
    editPet,
    // Aliases for component ergonomics
    deletePet: removePet,
    updatePet: editPet,
  };
});

// Persist: enable pinia-plugin-persistedstate in nuxt.config.ts to auto-persist this store to localStorage
