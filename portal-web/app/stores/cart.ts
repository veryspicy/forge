// Forge — Cart Store (backend-persisted)
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";
import { useRegion } from "~/composables/useRegion";

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
  // 税费口径由后端按收货辖区（静态税率表）返回，避免前端硬编码税率
  const taxLabel = ref("Tax");
  const taxRate = ref(0);
  const taxInclusive = ref(false);
  const shipping = ref(0);
  /** 后端返回的应付总额（含税/运费），优先使用，避免前端各算一套 */
  const serverTotal = ref<number | null>(null);
  const currency = ref("USD");

  const { fetchCart, addToCart, updateCartItem, removeCartItem, clearCart } = useApi();

  const itemCount = computed(() => items.value.reduce((sum, i) => sum + i.quantity, 0));
  const subtotal = computed(() => items.value.reduce((sum, i) => sum + i.product.price * i.quantity, 0));

  const total = computed(() =>
    serverTotal.value !== null
      ? serverTotal.value - discount.value
      : subtotal.value + (taxInclusive.value ? 0 : tax.value) + shipping.value - discount.value,
  );

  const isEmpty = computed(() => items.value.length === 0);

  const loadCart = async (jurisdiction?: { country?: string; region?: string }) => {
    loading.value = true;
    try {
      const regionStore = useRegion();
      const result: any = await fetchCart(
        jurisdiction ?? { country: regionStore.region.value },
      );
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
      taxRate.value = result.tax_rate || 0;
      taxLabel.value = result.tax_label || result.tax_name || "Tax";
      taxInclusive.value = !!result.tax_inclusive;
      // 后端字段为 shipping_cost；兼容旧的 shipping 命名
      shipping.value = result.shipping_cost ?? result.shipping ?? 0;
      serverTotal.value = typeof result.total === "number" ? result.total : null;
      currency.value = result.currency || "USD";
      loaded.value = true;
    } catch {
      /* ignore — auth required, page middleware handles this */
    } finally {
      loading.value = false;
    }
  };

  const addItem = async (item: { product: CartProduct; quantity: number }) => {
    // 不再静默吞异常：未登录（401）或校验失败必须抛给调用方，避免「加购成功」假象
    await addToCart({
      product_id: item.product.id,
      name: item.product.name,
      price: item.product.price,
      quantity: item.quantity,
      image: item.product.image || "",
    });
    // Refresh cart from server to stay in sync
    await loadCart();
  };

  const removeItem = async (productId: string) => {
    const cartItem = items.value.find((i) => i.product.id === productId);
    if (!cartItem) return;
    try {
      await removeCartItem(cartItem.cartItemId);
      // Refresh cart from server to stay in sync
      await loadCart();
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
      serverTotal.value = null;
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
    taxLabel,
    taxRate,
    taxInclusive,
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
