// Forge — API composable
import type { UseFetchOptions } from "nuxt/app";
import { useAuthStore } from "~/stores/auth";

const API_BASE = useRuntimeConfig().public.apiBase;

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function authFetch(url: string, opts: any = {}) {
  const headers = { ...getAuthHeaders(), ...(opts.headers || {}) };
  return $fetch(url, { ...opts, headers });
}

export function useApi() {
  const fetchProducts = async (params?: Record<string, any>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return authFetch(`${API_BASE}/products${query}`);
  };

  const fetchProduct = async (id: string) => {
    return authFetch(`${API_BASE}/products/${id}`);
  };

  const fetchPets = async () => {
    return authFetch(`${API_BASE}/pets/`);
  };

  const fetchPet = async (id: string) => {
    return authFetch(`${API_BASE}/pets/${id}`);
  };

  const createPet = async (data: any) => {
    return authFetch(`${API_BASE}/pets/`, {
      method: "POST",
      body: data,
    });
  };

  const fetchOrders = async (params?: Record<string, any>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return authFetch(`${API_BASE}/orders${query}`);
  };

  const createOrder = async (data: any): Promise<any> => {
    return (await authFetch(`${API_BASE}/orders`, {
      method: "POST",
      body: data,
    })) as any;
  };

  const fetchRegions = async () => {
    return authFetch(`${API_BASE}/regions`);
  };

  const aiChat = async (data: { message: string; conversation_id?: string; pet_id?: string }) => {
    return authFetch(`${API_BASE}/ai/chat`, {
      method: "POST",
      body: data,
    });
  };

  // Product recommendations
  const fetchRecommendations = async (params?: Record<string, any>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return authFetch(`${API_BASE}/products/recommendations${query}`);
  };

  // Pet recommendations
  const fetchPetRecommendations = async (petId: string) => {
    return authFetch(`${API_BASE}/pets/${petId}/recommendations`);
  };

  const updatePet = async (id: string, data: any) => {
    return authFetch(`${API_BASE}/pets/${id}`, {
      method: "PATCH",
      body: data,
    });
  };

  const deletePet = async (id: string) => {
    return authFetch(`${API_BASE}/pets/${id}`, {
      method: "DELETE",
    });
  };

  // Order detail / cancel / tracking
  const fetchOrderDetail = async (orderNumber: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}`);
  };

  const cancelOrder = async (orderNumber: string, reason?: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}/cancel`, {
      method: "POST",
      body: { reason },
    });
  };

  const fetchTracking = async (orderNumber: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}/tracking`);
  };

  // Shipments
  const fetchShipments = async (orderId: string): Promise<any[]> => {
    return (await authFetch(`${API_BASE}/orders/${orderId}/shipments`)) as any[];
  };

  // Conversations
  const fetchConversations = async () => {
    return authFetch(`${API_BASE}/ai/conversations`);
  };

  const deleteConversation = async (id: string) => {
    return authFetch(`${API_BASE}/ai/conversations/${id}`, {
      method: "DELETE",
    });
  };

  // Cart
  const fetchCart = async (): Promise<{
    items: Array<{
      id: string; user_id: string; product_id: string;
      name: string; price: number; quantity: number;
      image: string; subtotal: number;
    }>;
    item_count: number; subtotal: number; tax: number;
    shipping: number; total: number;
  }> => {
    return authFetch(`${API_BASE}/cart/items`) as any;
  };

  const addToCart = async (data: {
    product_id: string; name: string; price: number;
    quantity: number; image: string;
  }) => {
    return authFetch(`${API_BASE}/cart/items`, {
      method: "POST",
      body: data,
    });
  };

  const updateCartItem = async (itemId: string, quantity: number) => {
    return authFetch(`${API_BASE}/cart/items/${itemId}`, {
      method: "PUT",
      body: { quantity },
    });
  };

  const removeCartItem = async (itemId: string) => {
    return authFetch(`${API_BASE}/cart/items/${itemId}`, {
      method: "DELETE",
    });
  };

  const clearCart = async () => {
    return authFetch(`${API_BASE}/cart/items`, {
      method: "DELETE",
    });
  };

  return {
    fetchProducts,
    fetchProduct,
    fetchPets,
    fetchPet,
    createPet,
    updatePet,
    deletePet,
    fetchOrders,
    createOrder,
    fetchOrderDetail,
    cancelOrder,
    fetchTracking,
    fetchShipments,
    fetchRegions,
    aiChat,
    fetchRecommendations,
    fetchPetRecommendations,
    fetchConversations,
    deleteConversation,
    fetchCart,
    addToCart,
    updateCartItem,
    removeCartItem,
    clearCart,
  };
}
