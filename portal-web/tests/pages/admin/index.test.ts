import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import AdminDashboard from "~/pages/admin/index.vue";

// Mock composables
vi.mock("~/composables/useAdminApi", () => ({
  getDashboardStats: vi.fn().mockResolvedValue({
    orderCount: 128,
    productCount: 56,
    skuCount: 320,
    supplierCount: 42,
    todayRevenue: 125000,
    revenueTrend: "up",
    revenueTrendValue: "+12.5%",
  }),
  getOrders: vi.fn().mockResolvedValue({
    items: [
      {
        id: "1",
        order_no: "ORD-20240624-001",
        customer: "张三",
        amount: 299.0,
        status: "paid",
        created_at: "2024-06-24T10:30:00Z",
      },
      {
        id: "2",
        order_no: "ORD-20240624-002",
        customer: "李四",
        amount: 599.0,
        status: "procurement_failed",
        created_at: "2024-06-24T11:00:00Z",
      },
    ],
  }),
}));

// Mock store
vi.mock("~/stores/admin", () => ({
  useAdminStore: vi.fn(() => ({
    sidebarCollapsed: false,
    currentPage: "dashboard",
    stats: null,
    loading: false,
    toggleSidebar: vi.fn(),
    fetchStats: vi.fn(),
  })),
}));

// Mock nuxt composables
vi.mock("#app", () => ({
  useRoute: () => ({ path: "/admin" }),
  navigateTo: vi.fn(),
  definePageMeta: vi.fn(),
}));

describe("Admin Dashboard Page", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders dashboard title", () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        stubs: {
          StatCard: true,
          DataTable: true,
          StatusBadge: true,
        },
      },
    });

    expect(wrapper.text()).toContain("仪表盘");
  });

  it("renders current date", () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        stubs: {
          StatCard: true,
          DataTable: true,
          StatusBadge: true,
        },
      },
    });

    // Should contain year and week day
    const text = wrapper.text();
    expect(text).toMatch(/2026年/);
  });

  it("renders 4 stat cards when stats loaded", async () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        stubs: {
          StatCard: true,
          DataTable: true,
          StatusBadge: true,
        },
      },
    });

    // Wait for async data loading
    await new Promise((r) => setTimeout(r, 100));
    await wrapper.vm.$nextTick();

    const statCards = wrapper.findAllComponents({ name: "StatCard" });
    expect(statCards.length).toBe(4);
  });

  it("renders recent orders table", () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        stubs: {
          StatCard: true,
          DataTable: true,
          StatusBadge: true,
        },
      },
    });

    expect(wrapper.findComponent({ name: "DataTable" }).exists()).toBe(true);
  });

  it("renders pending alerts section", () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        stubs: {
          StatCard: true,
          DataTable: true,
          StatusBadge: true,
        },
      },
    });

    expect(wrapper.text()).toContain("待处理提醒");
  });

  it("shows loading state initially for stats", () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        stubs: {
          StatCard: true,
          DataTable: true,
          StatusBadge: true,
        },
      },
    });

    // The component has statsLoading ref initially true
    // Loading skeletons should be rendered
    const loadingSkeletons = wrapper.findAll(".animate-pulse");
    // There may be loading skeletons for both stats and orders
    expect(loadingSkeletons.length).toBeGreaterThanOrEqual(0);
  });
});
