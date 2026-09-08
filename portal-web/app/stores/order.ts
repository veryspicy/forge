// Forge — Order Store
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

export const useOrderStore = defineStore("order", () => {
  const orders = ref<any[]>([]);
  const loading = ref(false);
  const currentOrder = ref<any | null>(null);
  const shipments = ref<any[]>([]);

  const { fetchOrders, createOrder, fetchOrderDetail, cancelOrder, payOrder, confirmReceipt, updateShippingAddress, deleteOrder, fetchTracking, fetchShipments, fetchMyReviews, submitReview, deleteMyReview } = useApi();

  const loadOrders = async (params?: Record<string, any>) => {
    loading.value = true;
    try {
      const result: any = await fetchOrders(params);
      orders.value = result.items || [];
    } catch {
      orders.value = [];
    } finally {
      loading.value = false;
    }
  };

  const placeOrder = async (data: any) => {
    try {
      const order = await createOrder(data);
      return order;
    } catch (error: any) {
      throw error;
    }
  };

  const loadOrderDetail = async (orderNumber: string) => {
    loading.value = true;
    try {
      currentOrder.value = (await fetchOrderDetail(orderNumber)) as any;
    } finally {
      loading.value = false;
    }
  };

  const cancelExistingOrder = async (orderNumber: string, reason?: string) => {
    const result = await cancelOrder(orderNumber, reason);
    const patch = { ...result, status: result?.status ?? "cancelled" };
    const idx = orders.value.findIndex((o) => o.order_number === orderNumber || o.id === orderNumber);
    if (idx !== -1) {
      orders.value[idx] = { ...orders.value[idx], ...patch };
    }
    if (currentOrder.value?.order_number === orderNumber || currentOrder.value?.id === orderNumber) {
      currentOrder.value = { ...currentOrder.value, ...patch };
    }
    return result;
  };

  const payExistingOrder = async (orderNumber: string, data: { payment_method: string; card?: Record<string, string> }) => {
    const result = await payOrder(orderNumber, data);
    patchLocal(orderNumber, result);
    return result;
  };

  const confirmReceiptOrder = async (orderNumber: string) => {
    const result = await confirmReceipt(orderNumber);
    patchLocal(orderNumber, result);
    return result;
  };

  const updateShippingAddressForOrder = async (orderNumber: string, shippingAddress: Record<string, any>) => {
    const result = await updateShippingAddress(orderNumber, shippingAddress);
    patchLocal(orderNumber, result);
    return result;
  };

  const deleteExistingOrder = async (orderNumber: string) => {
    await deleteOrder(orderNumber);
    orders.value = orders.value.filter((o) => o.order_number !== orderNumber && o.id !== orderNumber);
    if (currentOrder.value?.order_number === orderNumber || currentOrder.value?.id === orderNumber) {
      currentOrder.value = null;
    }
    return true;
  };

  const reviewedItemIds = ref<Set<string>>(new Set());
  const loadMyReviews = async () => {
    try {
      const result: any = await fetchMyReviews({ page_size: 100 });
      reviewedItemIds.value = new Set((result.items || []).map((r: any) => String(r.order_item_id)));
      return result;
    } catch {
      reviewedItemIds.value = new Set();
      return { items: [] };
    }
  };

  const submitProductReview = async (data: { order_number: string; order_item_id: string; rating: number; title?: string; content?: string; images?: string[] }) => {
    const result = await submitReview(data);
    reviewedItemIds.value.add(String(data.order_item_id));
    return result;
  };

  const removeMyReview = async (reviewId: string) => {
    const result = await deleteMyReview(reviewId);
    await loadMyReviews();
    return result;
  };

  function patchLocal(orderNumber: string, patch: Record<string, any>) {
    const idx = orders.value.findIndex((o) => o.order_number === orderNumber || o.id === orderNumber);
    if (idx !== -1) {
      orders.value[idx] = { ...orders.value[idx], ...patch };
    }
    if (currentOrder.value?.order_number === orderNumber || currentOrder.value?.id === orderNumber) {
      currentOrder.value = { ...currentOrder.value, ...patch };
    }
  }

  const loadTracking = async (orderNumber: string) => {
    const tracking = await fetchTracking(orderNumber);
    return tracking;
  };

  const loadShipments = async (orderId: string) => {
    try {
      shipments.value = await fetchShipments(orderId);
      return shipments.value;
    } catch {
      shipments.value = [];
      return [];
    }
  };

  return {
    orders,
    loading,
    currentOrder,
    shipments,
    reviewedItemIds,
    loadOrders,
    placeOrder,
    loadOrderDetail,
    cancelOrder: cancelExistingOrder,
    payOrder: payExistingOrder,
    confirmReceipt: confirmReceiptOrder,
    updateShippingAddress: updateShippingAddressForOrder,
    deleteOrder: deleteExistingOrder,
    loadMyReviews,
    submitReview: submitProductReview,
    removeMyReview,
    loadTracking,
    loadShipments,
  };
});
