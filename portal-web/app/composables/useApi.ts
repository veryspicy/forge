// Forge — API composable
import { useAuthStore } from "~/stores/auth";

export function useApi() {
  const API_BASE = useRuntimeConfig().public.apiBase;

  function getAuthHeaders(): Record<string, string> {
    const token = useAuthStore().token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function authFetch<T = any>(url: string, opts: any = {}): Promise<T> {
    const headers = { ...getAuthHeaders(), ...(opts.headers || {}) };
    try {
      return (await $fetch(url, { ...opts, headers })) as T;
    } catch (err: any) {
      const status = err?.response?.status;
      // 会话失效（401/403）：清除 token 并回登录页，避免流程卡死
      if ((status === 401 || status === 403) && import.meta.client && getAuthHeaders().Authorization) {
        const authStore = useAuthStore();
        authStore.logout();
        const g = globalThis as any;
        if (!g.__forgeAuthRedirecting) {
          g.__forgeAuthRedirecting = true;
          const route = useRoute();
          const localePath = useLocalePath();
          const redirectPath = encodeURIComponent(route.fullPath || '/');
          navigateTo(localePath(`/login?redirect=${redirectPath}`));
        }
      }
      throw err;
    }
  }

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

  // Order detail / cancel / pay / receipt / delete / tracking
  const fetchOrderDetail = async (orderNumber: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}`);
  };

  const cancelOrder = async (orderNumber: string, reason?: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}/cancel`, {
      method: "POST",
      body: { reason },
    });
  };

  const payOrder = async (orderNumber: string, data: { payment_method: string; card?: Record<string, string> }) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}/pay`, {
      method: "POST",
      body: data,
    });
  };

  const confirmReceipt = async (orderNumber: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}/confirm-receipt`, {
      method: "POST",
    });
  };

  const updateShippingAddress = async (orderNumber: string, shippingAddress: Record<string, any>) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}/shipping-address`, {
      method: "POST",
      body: { shipping_address: shippingAddress },
    });
  };

  const deleteOrder = async (orderNumber: string) => {
    return authFetch(`${API_BASE}/orders/${orderNumber}`, {
      method: "DELETE",
    });
  };

  // Product reviews
  const fetchMyReviews = async (params?: Record<string, any>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return authFetch(`${API_BASE}/reviews/mine${query}`);
  };

  const submitReview = async (data: {
    order_number: string;
    order_item_id: string;
    rating: number;
    title?: string;
    content?: string;
    images?: string[];
  }) => {
    return authFetch(`${API_BASE}/reviews`, {
      method: "POST",
      body: data,
    });
  };

  const deleteMyReview = async (reviewId: string) => {
    return authFetch(`${API_BASE}/reviews/${reviewId}`, {
      method: "DELETE",
    });
  };

  const fetchProductReviews = async (productId: string | number, params?: Record<string, any>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return authFetch(`${API_BASE}/products/${productId}/reviews${query}`);
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
    payOrder,
    confirmReceipt,
    updateShippingAddress,
    deleteOrder,
    fetchTracking,
    fetchShipments,
    fetchMyReviews,
    submitReview,
    deleteMyReview,
    fetchProductReviews,
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
