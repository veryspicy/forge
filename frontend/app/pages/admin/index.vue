<script setup lang="ts">
import { getDashboardStats, getOrders } from "~/composables/useAdminApi";

definePageMeta({
  layout: "admin",
  middleware: "auth",
});

const store = useAdminStore();

// Date display
const todayDate = computed(() => {
  const d = new Date();
  const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`;
});

// Stats
const statsLoading = ref(true);
const stats = ref<{
  orderCount: number;
  productCount: number;
  skuCount: number;
  supplierCount: number;
  todayRevenue: number;
  revenueTrend: "up" | "down" | "neutral";
  revenueTrendValue: string;
} | null>(null);

async function loadStats() {
  statsLoading.value = true;
  try {
    const data: any = await getDashboardStats();
    stats.value = {
      orderCount: data.orderCount ?? data.order_count ?? 0,
      productCount: data.productCount ?? data.product_count ?? 0,
      skuCount: data.skuCount ?? data.sku_count ?? 0,
      supplierCount: data.supplierCount ?? data.supplier_count ?? 0,
      todayRevenue: data.todayRevenue ?? data.today_revenue ?? 0,
      revenueTrend: data.revenueTrend ?? data.revenue_trend ?? "neutral",
      revenueTrendValue: data.revenueTrendValue ?? data.revenue_trend_value ?? "",
    };
  } catch {
    stats.value = null;
  } finally {
    statsLoading.value = false;
  }
}

// Recent orders
const ordersLoading = ref(true);
const recentOrders = ref<any[]>([]);

const orderColumns = [
  { key: "order_no", label: "订单号", sortable: false },
  { key: "customer", label: "客户", sortable: false },
  { key: "amount", label: "金额", sortable: true, align: "right" as const },
  { key: "status", label: "状态", sortable: false },
  { key: "created_at", label: "时间", sortable: true },
];

async function loadRecentOrders() {
  ordersLoading.value = true;
  try {
    const data: any = await getOrders({ limit: 10 });
    recentOrders.value = (data?.items ?? data?.orders ?? data?.results ?? []).slice(0, 10);
  } catch {
    recentOrders.value = [];
  } finally {
    ordersLoading.value = false;
  }
}

// Alerts
const alerts = computed(() => {
  const pendingAudit = stats.value?.orderCount ?? 0;
  const procurementIssues = recentOrders.value.filter(
    (o: any) => o.status === "procurement_failed" || o.status === "采购异常"
  ).length;
  return { pendingAudit, procurementIssues };
});

function formatCurrency(val: number): string {
  return `¥${val.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatTime(raw: string): string {
  if (!raw) return "-";
  const d = new Date(raw);
  if (isNaN(d.getTime())) return raw;
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function goToOrders() {
  navigateTo("/admin/orders");
}

function goToOrdersWithFilter(status: string) {
  navigateTo(`/admin/orders?status=${status}`);
}

onMounted(() => {
  loadStats();
  loadRecentOrders();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-2xl font-heading font-bold tracking-tight text-neutral-900">
          仪表盘
        </h1>
        <p class="mt-0.5 text-sm text-neutral-500">{{ todayDate }}</p>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <!-- Loading skeletons -->
      <template v-if="statsLoading">
        <div v-for="i in 4" :key="i" class="rounded bg-primary-50 border border-primary-100 px-5 py-4 animate-pulse">
          <div class="h-3 w-16 rounded bg-primary-200" />
          <div class="mt-2 h-7 w-24 rounded bg-primary-200" />
        </div>
      </template>

      <template v-else-if="stats">
        <StatCard
          title="今日订单数"
          :value="String(stats.orderCount)"
        />
        <StatCard
          :title="`商品总数 (SKU ${stats.skuCount})`"
          :value="String(stats.productCount)"
        />
        <StatCard
          title="活跃供应商"
          :value="String(stats.supplierCount)"
        />
        <StatCard
          title="今日销售额"
          :value="formatCurrency(stats.todayRevenue)"
          :trend="stats.revenueTrend"
          :trend-value="stats.revenueTrendValue"
        />
      </template>
    </div>

    <!-- Alerts + Orders grid -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_240px]">
      <!-- Recent orders table -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold tracking-wide text-neutral-700 uppercase">
            最近订单
          </h2>
          <button
            class="text-xs font-medium text-accent-600 hover:text-accent-700 transition-colors"
            @click="goToOrders"
          >
            查看全部
          </button>
        </div>

        <DataTable
          :columns="orderColumns"
          :data="recentOrders"
          :loading="ordersLoading"
        >
          <template #order_no="{ value }">
            <span class="font-mono text-xs text-neutral-600">{{ value }}</span>
          </template>
          <template #amount="{ value }">
            <span class="tabular-nums font-medium text-neutral-800">
              {{ formatCurrency(Number(value)) }}
            </span>
          </template>
          <template #status="{ value }">
            <StatusBadge :status="value" />
          </template>
          <template #created_at="{ value }">
            <span class="text-neutral-500 tabular-nums text-xs">
              {{ formatTime(value) }}
            </span>
          </template>
        </DataTable>
      </div>

      <!-- Pending alerts -->
      <div class="space-y-3">
        <h2 class="text-sm font-semibold tracking-wide text-neutral-700 uppercase mb-4">
          待处理提醒
        </h2>

        <!-- Pending audit orders -->
        <button
          class="w-full rounded border border-red-200 bg-red-50 px-4 py-3.5 text-left transition-colors hover:bg-red-100/70"
          @click="goToOrdersWithFilter('pending_audit')"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm text-red-800">待审核订单</span>
            <span class="inline-flex size-6 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white tabular-nums">
              {{ alerts.pendingAudit }}
            </span>
          </div>
          <p class="mt-1 text-xs text-red-600">需尽快审核处理</p>
        </button>

        <!-- Procurement issues -->
        <button
          class="w-full rounded border border-amber-200 bg-amber-50 px-4 py-3.5 text-left transition-colors hover:bg-amber-100/70"
          @click="goToOrdersWithFilter('procurement_failed')"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm text-amber-800">采购异常</span>
            <span class="inline-flex size-6 items-center justify-center rounded-full bg-amber-500 text-xs font-bold text-white tabular-nums">
              {{ alerts.procurementIssues }}
            </span>
          </div>
          <p class="mt-1 text-xs text-amber-600">需人工介入处理</p>
        </button>
      </div>
    </div>
  </div>
</template>
