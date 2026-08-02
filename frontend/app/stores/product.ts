// Forge — Product Store
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

interface Product {
  id: string;
  sku: string;
  slug: string;
  name: string;
  description: string;
  price: number;
  original_price?: number;
  category: string;
  breed_groups: string[];
  inventory: number;
  rating: number;
  review_count?: number;
  images: string[];
  tags?: string[];
  is_ai_generated?: boolean;
  variants?: any[];
  weight?: string;
  dimensions?: string;
  material?: string;
  ingredients?: string;
}

interface ProductFilters {
  category?: string;
  breed_group?: string;
  search?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export const useProductStore = defineStore("product", () => {
  const products = ref<Product[]>([]);
  const currentProduct = ref<Product | null>(null);
  const loading = ref(false);
  const total = ref(0);
  const recommendations = ref<any[]>([]);
  const currentPage = ref(1);

  const { fetchProducts, fetchProduct, fetchRecommendations } = useApi();

  const totalPages = computed(() => {
    const pageSize = 20; // default page size
    return Math.max(1, Math.ceil(total.value / pageSize));
  });

  const loadProducts = async (filters?: ProductFilters) => {
    loading.value = true;
    try {
      const result: any = await fetchProducts(filters as any);
      products.value = result.items || [];
      total.value = result.total || 0;
      if (filters?.page) {
        currentPage.value = filters.page;
      }
    } catch {
      products.value = [];
      total.value = 0;
    } finally {
      loading.value = false;
    }
  };

  const loadProduct = async (id: string) => {
    loading.value = true;
    try {
      currentProduct.value = (await fetchProduct(id)) as any;
    } catch {
      currentProduct.value = null;
    } finally {
      loading.value = false;
    }
  };

  const loadRecommendations = async (params?: Record<string, any>) => {
    try {
      const result: any = await fetchRecommendations(params);
      recommendations.value = result.items || result || [];
    } catch {
      recommendations.value = [];
    }
  };

  return {
    products,
    currentProduct,
    loading,
    total,
    recommendations,
    currentPage,
    totalPages,
    loadProducts,
    loadProduct,
    loadRecommendations,
  };
});
