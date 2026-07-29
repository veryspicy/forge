// Forge — Cart Store (backend-persisted)
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

interface CartProduct {
  id: string;
  name: string;
  price: number;
  image?: string;
}

interface CartItem {
  cartItemId: string;      // backend cart item ID for update/delete
  product: CartProduct;
  quantity: number;
}

export const useCartStore = defineStore("cart", () => {
  const items = ref<CartItem[]>([]);
  const loading = ref(false);
  const loaded = ref(false);

  const couponCode = ref<string | null>(null);
  const discount = ref(0);
  const tax = ref(0);
  const shipping = ref(0);
  const currency = ref("USD");

  const { fetchCart, addToCart, updateCartItem, removeCartItem, clearCart } = useApi();

  const itemCount = computed(() => items.value.reduce((sum, i) => sum + i.quantity, 0));
  const subtotal = computed(() => items.value.reduce((sum, i) => sum + i.product.price * i.quantity, 0));

  const total = computed(() => subtotal.value + tax.value + shipping.value - discount.value);

  const isEmpty = computed(() => items.value.length === 0);

  const loadCart = async () => {
    loading.value = true;
    try {
      const result: any = await fetchCart();
      items.value = (result.items || []).map((item: any) => ({
        cartItemId: item.id,
        product: {
          id: item.product_id,
          name: item.name,
          price: item.price,
          image: item.image,
        },
        quantity: item.quantity,
      }));
      tax.value = result.tax || 0;
      shipping.value = result.shipping || 0;
      currency.value = result.currency || "USD";
      loaded.value = true;
    } catch {
      /* ignore — auth required, page middleware handles this */
    } finally {
      loading.value = false;
    }
  };

  const addItem = async (item: { product: CartProduct; quantity: number }) => {
    try {
      const result: any = await addToCart({
        product_id: item.product.id,
        name: item.product.name,
        price: item.product.price,
        quantity: item.quantity,
        image: item.product.image || "",
      });
      // Refresh cart from server to stay in sync
      await loadCart();
    } catch {
      /* ignore */
    }
  };

  const removeItem = async (productId: string) => {
    const cartItem = items.value.find((i) => i.product.id === productId);
    if (!cartItem) return;
    try {
      await removeCartItem(cartItem.cartItemId);
      items.value = items.value.filter((i) => i.product.id !== productId);
    } catch {
      /* ignore */
    }
  };

  const updateQuantity = async (productId: string, quantity: number) => {
    const cartItem = items.value.find((i) => i.product.id === productId);
    if (!cartItem) return;
    if (quantity <= 0) {
      await removeItem(productId);
      return;
    }
    try {
      await updateCartItem(cartItem.cartItemId, quantity);
      cartItem.quantity = quantity;
    } catch {
      /* ignore */
    }
  };

  const cleanCart = async () => {
    try {
      await clearCart();
      items.value = [];
      couponCode.value = null;
      discount.value = 0;
      tax.value = 0;
      shipping.value = 0;
    } catch {
      /* ignore */
    }
  };

  const applyCoupon = (code: string) => {
    if (code === "SAVE10") {
      couponCode.value = code;
      discount.value = subtotal.value * 0.1;
      return true;
    }
    return false;
  };

  const removeCoupon = () => {
    couponCode.value = null;
    discount.value = 0;
  };

  return {
    items,
    itemCount,
    subtotal,
    total,
    isEmpty,
    loading,
    loaded,
    couponCode,
    discount,
    tax,
    shipping,
    currency,
    loadCart,
    addItem,
    removeItem,
    updateQuantity,
    clearCart: cleanCart,
    applyCoupon,
    removeCoupon,
  };
});
