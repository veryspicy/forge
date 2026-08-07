// Forge — Admin Store
import { defineStore } from "pinia";

export const useAdminStore = defineStore("admin", () => {
  const sidebarCollapsed = ref(false);
  const currentPage = ref("dashboard");
  const stats = ref<{
    orderCount: number;
    productCount: number;
    supplierCount: number;
    todayRevenue: number;
  } | null>(null);
  const loading = ref(false);

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  };

  const fetchStats = async () => {
    loading.value = true;
    try {
      const { getDashboardStats } = await import("~/composables/useAdminApi");
      const data: any = await getDashboardStats();
      stats.value = data;
    } catch (e) {
      console.error("[Admin] Failed to fetch stats:", e);
    } finally {
      loading.value = false;
    }
  };

  return {
    sidebarCollapsed,
    currentPage,
    stats,
    loading,
    toggleSidebar,
    fetchStats,
  };
});
