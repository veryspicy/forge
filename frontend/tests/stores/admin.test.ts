import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAdminStore } from "~/stores/admin";

describe("admin store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("initial state - sidebarCollapsed is false", () => {
    const store = useAdminStore();
    expect(store.sidebarCollapsed).toBe(false);
  });

  it("initial state - currentPage is dashboard", () => {
    const store = useAdminStore();
    expect(store.currentPage).toBe("dashboard");
  });

  it("initial state - stats is null", () => {
    const store = useAdminStore();
    expect(store.stats).toBeNull();
  });

  it("initial state - loading is false", () => {
    const store = useAdminStore();
    expect(store.loading).toBe(false);
  });

  it("toggleSidebar toggles state", () => {
    const store = useAdminStore();
    expect(store.sidebarCollapsed).toBe(false);

    store.toggleSidebar();
    expect(store.sidebarCollapsed).toBe(true);

    store.toggleSidebar();
    expect(store.sidebarCollapsed).toBe(false);
  });

  it("fetchStats populates stats on success", async () => {
    const mockData = {
      orderCount: 100,
      productCount: 50,
      supplierCount: 20,
      todayRevenue: 50000,
    };

    // Mock the dynamic import
    vi.doMock("~/composables/useAdminApi", () => ({
      getDashboardStats: vi.fn().mockResolvedValue(mockData),
    }));

    const store = useAdminStore();
    expect(store.stats).toBeNull();

    await store.fetchStats();
    expect(store.stats).toEqual(mockData);
    expect(store.loading).toBe(false);
  });

  it("fetchStats handles API error gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    vi.doMock("~/composables/useAdminApi", () => ({
      getDashboardStats: vi.fn().mockRejectedValue(new Error("Network Error")),
    }));

    const store = useAdminStore();
    await store.fetchStats();

    // stats should remain null on error
    expect(store.stats).toBeNull();
    // loading should be reset to false
    expect(store.loading).toBe(false);
    // error should be logged
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it("fetchStats sets loading to true during fetch", () => {
    const store = useAdminStore();
    // loading is initially false
    expect(store.loading).toBe(false);
    // We verify loading becomes true during fetch by calling fetchStats
    // which internally sets loading = true before the async call
    const promise = store.fetchStats();
    expect(store.loading).toBe(true);
    return promise;
  });
});
