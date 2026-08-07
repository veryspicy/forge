// Forge — Order Store
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

export const useOrderStore = defineStore("order", () => {
  const orders = ref<any[]>([]);
  const loading = ref(false);
  const currentOrder = ref<any | null>(null);
  const shipments = ref<any[]>([]);

  const { fetchOrders, createOrder, fetchOrderDetail, cancelOrder, fetchTracking, fetchShipments } = useApi();

  const loadOrders = async (params?: Record<string, any>) => {
    loading.value = true;
    try {
      const result: any = await fetchOrders(params);
      orders.value = result.items || [];
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
    const idx = orders.value.findIndex((o) => o.order_number === orderNumber || o.id === orderNumber);
    if (idx !== -1) {
      orders.value[idx] = { ...orders.value[idx], status: "CANCELLED" };
    }
    if (currentOrder.value?.order_number === orderNumber || currentOrder.value?.id === orderNumber) {
      currentOrder.value = { ...currentOrder.value, status: "CANCELLED" };
    }
    return result;
  };

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
    loadOrders,
    placeOrder,
    loadOrderDetail,
    cancelOrder: cancelExistingOrder,
    loadTracking,
    loadShipments,
  };
});
