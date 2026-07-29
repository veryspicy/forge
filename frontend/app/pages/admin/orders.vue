<script setup lang="ts">
import {
  getOrders,
  approveOrder,
  rejectOrder,
  startProcurement,
} from "~/composables/useAdminApi";

definePageMeta({
  layout: "admin",
  middleware: "auth",
});

// ──────────────────────── Types ────────────────────────

interface OrderItem {
  id: string;
  name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

interface TimelineEntry {
  label: string;
  time: string;
  active: boolean;
}

interface Order {
  id: string;
  order_no: string;
  customer_name: string;
  customer_phone?: string;
  item_count: number;
  total_amount: number;
  status: string;
  created_at: string;
  paid_at?: string;
  items?: OrderItem[];
  shipping_address?: string;
  tracking_no?: string;
  logistics_info?: string;
  timeline?: TimelineEntry[];
}

const statusLabels: Record<string, string> = {
  pending_payment: "待支付",
  paid: "已支付(待处理)",
  procuring: "采购中",
  shipped: "已发货",
  in_transit: "运输中",
  delivered: "已送达",
  completed: "已完成",
  procurement_failed: "采购异常",
};

const statusColors: Record<string, string> = {
  pending_payment: "oklch(0.65 0.16 85)",
  paid: "oklch(0.50 0.12 250)",
  procuring: "oklch(0.45 0.10 280)",
  shipped: "oklch(0.50 0.12 180)",
  in_transit: "oklch(0.55 0.12 200)",
  delivered: "oklch(0.55 0.15 160)",
  completed: "oklch(0.45 0.01 145)",
  procurement_failed: "oklch(0.52 0.18 25)",
};

const statusKeys = [
  "pending_payment",
  "paid",
  "procuring",
  "shipped",
  "in_transit",
  "delivered",
  "completed",
  "procurement_failed",
];

const statusLightColors: Record<string, string> = {
  pending_payment: "oklch(0.96 0.04 85 / 0.55)",
  paid: "oklch(0.94 0.04 250 / 0.50)",
  procuring: "oklch(0.94 0.03 280 / 0.45)",
  shipped: "oklch(0.94 0.04 180 / 0.45)",
  in_transit: "oklch(0.95 0.04 200 / 0.45)",
  delivered: "oklch(0.95 0.06 160 / 0.45)",
  completed: "oklch(0.95 0.01 145 / 0.45)",
  procurement_failed: "oklch(0.94 0.05 25 / 0.45)",
};

// ──────────────────────── Table config ────────────────────────

const columns = [
  { key: "order_no", label: "订单号", sortable: true },
  { key: "customer_name", label: "客户", sortable: true },
  { key: "item_count", label: "商品数", sortable: true, align: "center" as const },
  { key: "total_amount", label: "金额", sortable: true, align: "right" as const },
  { key: "status", label: "状态", sortable: false },
  { key: "created_at", label: "下单时间", sortable: true },
  { key: "actions", label: "操作", sortable: false, width: "200px" },
];

// ──────────────────────── State ────────────────────────

const loading = ref(false);
const orders = ref<Order[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);

const searchQuery = ref("");
const selectedStatuses = ref<string[]>([]);
const dateFrom = ref("");
const dateTo = ref("");

const expandedRowId = ref<string | null>(null);

// Review dialog state
const reviewDialogOpen = ref(false);
const reviewAction = ref<"approve" | "reject">("approve");
const reviewOrderId = ref("");
const rejectReason = ref("");

// Reprocess dialog state
const reprocessDialogOpen = ref(false);
const reprocessOrderId = ref("");

// ──────────────────────── Computed ────────────────────────

const hasActiveFilters = computed(() => {
  return selectedStatuses.value.length > 0 || dateFrom.value || dateTo.value;
});

// ──────────────────────── Data fetching ────────────────────────

async function fetchOrders(page = 1) {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page,
      per_page: 20,
    };
    if (searchQuery.value) params.search = searchQuery.value;
    if (selectedStatuses.value.length > 0) params.status = selectedStatuses.value.join(",");
    if (dateFrom.value) params.from_date = dateFrom.value;
    if (dateTo.value) params.to_date = dateTo.value;

    const res: any = await getOrders(params);
    orders.value = (res.data ?? res.items ?? res.orders ?? []) as Order[];
    totalPages.value = (res.total_pages ?? res.pages ?? 1) as number;
    currentPage.value = page;
  } catch (err) {
    console.error("Failed to fetch orders", err);
    orders.value = [];
  } finally {
    loading.value = false;
  }
}

// ──────────────────────── Status filter ────────────────────────

function toggleStatus(status: string) {
  const idx = selectedStatuses.value.indexOf(status);
  if (idx >= 0) {
    selectedStatuses.value.splice(idx, 1);
  } else {
    selectedStatuses.value.push(status);
  }
  fetchOrders(1);
}

function isStatusActive(status: string): boolean {
  return selectedStatuses.value.includes(status);
}

function clearFilters() {
  searchQuery.value = "";
  selectedStatuses.value = [];
  dateFrom.value = "";
  dateTo.value = "";
  fetchOrders(1);
}

// ──────────────────────── Row expansion ────────────────────────

function toggleRow(orderId: string) {
  expandedRowId.value = expandedRowId.value === orderId ? null : orderId;
}

function isExpanded(orderId: string): boolean {
  return expandedRowId.value === orderId;
}

// ──────────────────────── Review actions ────────────────────────

function openApprove(orderId: string) {
  reviewOrderId.value = orderId;
  reviewAction.value = "approve";
  rejectReason.value = "";
  reviewDialogOpen.value = true;
}

function openReject(orderId: string) {
  reviewOrderId.value = orderId;
  reviewAction.value = "reject";
  rejectReason.value = "";
  reviewDialogOpen.value = true;
}

async function confirmReview() {
  if (reviewAction.value === "reject" && !rejectReason.value.trim()) return;

  try {
    if (reviewAction.value === "approve") {
      await approveOrder(reviewOrderId.value);
    } else {
      await rejectOrder(reviewOrderId.value, rejectReason.value.trim());
    }
    reviewDialogOpen.value = false;
    fetchOrders(currentPage.value);
  } catch (err) {
    console.error("Review failed", err);
  }
}

function cancelReview() {
  reviewDialogOpen.value = false;
  rejectReason.value = "";
}

// ──────────────────────── Procurement actions ────────────────────────

async function handleStartProcurement(orderId: string) {
  try {
    await startProcurement(orderId);
    fetchOrders(currentPage.value);
  } catch (err) {
    console.error("Start procurement failed", err);
  }
}

function openReprocess(orderId: string) {
  reprocessOrderId.value = orderId;
  reprocessDialogOpen.value = true;
}

async function confirmReprocess() {
  try {
    await startProcurement(reprocessOrderId.value);
    reprocessDialogOpen.value = false;
    fetchOrders(currentPage.value);
  } catch (err) {
    console.error("Reprocess failed", err);
  }
}

function cancelReprocess() {
  reprocessDialogOpen.value = false;
}

// ──────────────────────── Export ────────────────────────

function handleExport() {
  const params: Record<string, any> = {};
  if (searchQuery.value) params.search = searchQuery.value;
  if (selectedStatuses.value.length > 0) params.status = selectedStatuses.value.join(",");
  if (dateFrom.value) params.from_date = dateFrom.value;
  if (dateTo.value) params.to_date = dateTo.value;

  const query = new URLSearchParams(params).toString();
  const url = `http://localhost:8000/api/admin/v1/orders/export?${query}`;
  window.open(url, "_blank");
}

// ──────────────────────── Formatting ────────────────────────

function formatCurrency(val: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(val);
}

function formatDate(val: string): string {
  if (!val) return "-";
  const d = new Date(val);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// ──────────────────────── Derived helpers ────────────────────────

function getStatusKey(raw: string): string {
  return raw.toLowerCase().replace(/[\s-]+/g, "_");
}

function getStatusLabel(raw: string): string {
  return statusLabels[getStatusKey(raw)] ?? raw;
}

function getStatusColor(raw: string): string {
  return statusColors[getStatusKey(raw)] ?? "oklch(0.55 0.00 145)";
}

function getStatusLightColor(raw: string): string {
  return statusLightColors[getStatusKey(raw)] ?? "oklch(0.95 0.01 145 / 0.40)";
}

// ──────────────────────── Lifecycle ────────────────────────

onMounted(() => {
  fetchOrders(1);
});
</script>

<template>
  <div class="space-y-5">
    <!-- Page title -->
    <div>
      <h1 class="text-xl font-bold tracking-tight text-neutral-900">订单管理</h1>
      <p class="mt-0.5 text-sm text-neutral-500">管理全款托管订单，审核与采购流程</p>
    </div>

    <!-- ──────────── Top toolbar ──────────── -->

    <!-- Search & date row -->
    <div class="flex flex-wrap items-end gap-3">
      <!-- Order number search -->
      <div class="flex-1 min-w-0 max-w-xs">
        <label class="block text-xs font-medium text-neutral-500 mb-1">搜索订单号</label>
        <div class="relative">
          <svg
            class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-neutral-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="输入订单号..."
            class="w-full rounded border border-neutral-300 bg-white py-1.5 pl-8 pr-3 text-sm text-neutral-800 placeholder-neutral-400 outline-none transition-shadow focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20"
            @keyup.enter="fetchOrders(1)"
          />
        </div>
      </div>

      <!-- Date from -->
      <div>
        <label class="block text-xs font-medium text-neutral-500 mb-1">开始日期</label>
        <input
          v-model="dateFrom"
          type="date"
          class="rounded border border-neutral-300 bg-white px-2.5 py-1.5 text-sm text-neutral-700 outline-none transition-shadow focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20"
          @change="fetchOrders(1)"
        />
      </div>

      <!-- Date to -->
      <div>
        <label class="block text-xs font-medium text-neutral-500 mb-1">结束日期</label>
        <input
          v-model="dateTo"
          type="date"
          class="rounded border border-neutral-300 bg-white px-2.5 py-1.5 text-sm text-neutral-700 outline-none transition-shadow focus:border-accent-400 focus:ring-2 focus:ring-accent-400/20"
          @change="fetchOrders(1)"
        />
      </div>

      <!-- Export -->
      <button
        class="inline-flex items-center gap-1.5 rounded border border-neutral-300 bg-white px-3.5 py-1.5 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-800"
        @click="handleExport"
      >
        <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        导出
      </button>
    </div>

    <!-- ──────────── Status filter pills ──────────── -->
    <div class="flex flex-wrap items-center gap-2">
      <!-- "All" pill -->
      <button
        :class="[
          'rounded-full px-3.5 py-1.5 text-xs font-medium transition-all duration-200',
          selectedStatuses.length === 0
            ? 'bg-neutral-800 text-white shadow-sm'
            : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200',
        ]"
        @click="selectedStatuses = []; fetchOrders(1)"
      >
        全部
      </button>

      <button
        v-for="sk in statusKeys"
        :key="sk"
        :class="[
          'rounded-full px-3.5 py-1.5 text-xs font-medium transition-all duration-200',
          isStatusActive(sk)
            ? 'text-white shadow-sm'
            : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200',
        ]"
        :style="isStatusActive(sk) ? { backgroundColor: getStatusColor(sk) } : {}"
        @click="toggleStatus(sk)"
      >
        {{ statusLabels[sk] }}
      </button>

      <button
        v-if="hasActiveFilters"
        class="ml-1 rounded-full px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
        @click="clearFilters"
      >
        清除筛选
      </button>
    </div>

    <!-- ──────────── Orders table ──────────── -->
    <div class="overflow-hidden rounded border border-neutral-200 bg-white">
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50 text-left">
              <!-- Expand toggle column -->
              <th class="w-10 px-2 py-2.5" />
              <th
                v-for="col in columns"
                :key="col.key"
                :class="[
                  'px-4 py-2.5 font-medium text-neutral-600',
                  col.align === 'right' && 'text-right',
                  col.align === 'center' && 'text-center',
                ]"
                :style="col.width ? { width: col.width } : {}"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <!-- Loading skeleton -->
            <tr v-if="loading">
              <td :colspan="columns.length + 1" class="px-4 py-12 text-center">
                <div class="space-y-2 px-8">
                  <div v-for="i in 4" :key="i" class="h-4 rounded bg-neutral-100 animate-pulse" />
                </div>
              </td>
            </tr>

            <!-- Empty state -->
            <tr v-else-if="orders.length === 0">
              <td :colspan="columns.length + 1" class="px-4 py-20 text-center">
                <p class="text-sm text-neutral-400">暂无订单数据</p>
                <p v-if="hasActiveFilters" class="mt-1 text-xs text-neutral-400">
                  尝试调整筛选条件
                </p>
              </td>
            </tr>

            <!-- Rows -->
            <template v-else>
              <template v-for="(order, oi) in orders" :key="order.id">
                <tr
                  class="border-b border-neutral-100 transition-colors hover:bg-neutral-50/60 cursor-pointer"
                  @click="toggleRow(order.id)"
                >
                  <td class="px-2 py-2.5">
                    <svg
                      class="size-3.5 text-neutral-400 transition-transform duration-250"
                      :class="{ 'rotate-90': isExpanded(order.id) }"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.5"
                    >
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  </td>
                  <td class="px-4 py-2.5 font-mono text-xs text-neutral-800">
                    {{ order.order_no }}
                  </td>
                  <td class="px-4 py-2.5 text-neutral-700">
                    {{ order.customer_name }}
                  </td>
                  <td class="px-4 py-2.5 text-center text-neutral-600">
                    {{ order.item_count }}
                  </td>
                  <td class="px-4 py-2.5 text-right font-semibold text-neutral-800 tabular-nums">
                    {{ formatCurrency(order.total_amount) }}
                  </td>
                  <td class="px-4 py-2.5">
                    <StatusBadge :status="order.status" />
                  </td>
                  <td class="px-4 py-2.5 text-xs text-neutral-500 tabular-nums">
                    {{ formatDate(order.created_at) }}
                  </td>
                  <td class="px-4 py-2.5" @click.stop>
                    <div class="flex items-center gap-1.5">
                      <!-- paid → approve / reject -->
                      <template v-if="getStatusKey(order.status) === 'paid'">
                        <button
                          class="rounded px-2.5 py-1 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors"
                          @click="openApprove(order.id)"
                        >
                          审核通过
                        </button>
                        <button
                          class="rounded px-2.5 py-1 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 transition-colors"
                          @click="openReject(order.id)"
                        >
                          拒绝
                        </button>
                      </template>

                      <!-- procuring → start procurement (if approved but not yet started) -->
                      <template v-else-if="getStatusKey(order.status) === 'procuring'">
                        <span class="text-xs text-neutral-400">采购进行中</span>
                      </template>

                      <!-- shipped / in_transit / delivered -->
                      <template
                        v-else-if="
                          ['shipped', 'in_transit', 'delivered', 'completed'].includes(
                            getStatusKey(order.status),
                          )
                        "
                      >
                        <span class="text-xs text-neutral-400">--</span>
                      </template>

                      <!-- procurement_failed → reprocess / cancel -->
                      <template v-else-if="getStatusKey(order.status) === 'procurement_failed'">
                        <button
                          class="rounded px-2.5 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition-colors"
                          @click="openReprocess(order.id)"
                        >
                          重新采购
                        </button>
                        <button
                          class="rounded px-2.5 py-1 text-xs font-medium text-neutral-600 bg-neutral-100 hover:bg-neutral-200 transition-colors"
                          @click="openReject(order.id)"
                        >
                          取消订单
                        </button>
                      </template>

                      <!-- pending_payment or other -->
                      <template v-else>
                        <span class="text-xs text-neutral-400">--</span>
                      </template>
                    </div>
                  </td>
                </tr>

                <!-- Expanded detail row -->
                <tr v-if="isExpanded(order.id)" class="border-b border-neutral-100 bg-neutral-50/40">
                  <td />
                  <td :colspan="columns.length" class="px-4 py-4">
                    <OrderDetailPanel :order="order" />
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        v-if="totalPages > 1"
        class="flex items-center justify-between border-t border-neutral-200 bg-neutral-50/50 px-4 py-2.5"
      >
        <span class="text-xs text-neutral-500">
          {{ currentPage }} / {{ totalPages }} 页
        </span>
        <div class="flex items-center gap-1">
          <button
            :disabled="currentPage <= 1"
            class="rounded px-2.5 py-1 text-xs text-neutral-600 hover:bg-neutral-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            @click="fetchOrders(currentPage - 1)"
          >
            上一页
          </button>
          <button
            :disabled="currentPage >= totalPages"
            class="rounded px-2.5 py-1 text-xs text-neutral-600 hover:bg-neutral-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            @click="fetchOrders(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <!-- ──────────── Review dialog ──────────── -->
    <Teleport to="body">
      <Transition name="dialog-fade">
        <div
          v-if="reviewDialogOpen"
          class="fixed inset-0 z-50 flex items-center justify-center"
          @click.self="cancelReview"
        >
          <!-- Backdrop -->
          <div class="absolute inset-0 bg-black/40" />

          <!-- Dialog -->
          <div class="relative w-full max-w-md rounded-lg bg-white shadow-xl">
            <div class="px-6 py-4 border-b border-neutral-200">
              <h3 class="text-base font-semibold text-neutral-900">
                {{ reviewAction === "approve" ? "审核通过" : "拒绝订单" }}
              </h3>
            </div>

            <div class="px-6 py-4">
              <p v-if="reviewAction === 'approve'" class="text-sm text-neutral-600">
                确认审核通过订单 <span class="font-mono text-neutral-800">{{ reviewOrderId }}</span>？
              </p>

              <template v-else>
                <p class="text-sm text-neutral-600 mb-3">
                  确认拒绝订单 <span class="font-mono text-neutral-800">{{ reviewOrderId }}</span>？
                </p>
                <label class="block text-xs font-medium text-neutral-500 mb-1">拒绝原因</label>
                <textarea
                  v-model="rejectReason"
                  rows="3"
                  placeholder="请输入拒绝原因..."
                  class="w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 placeholder-neutral-400 outline-none transition-shadow resize-none focus:border-red-400 focus:ring-2 focus:ring-red-400/20"
                />
              </template>
            </div>

            <div class="flex justify-end gap-2 px-6 py-4 border-t border-neutral-100 bg-neutral-50/50 rounded-b-lg">
              <button
                class="rounded px-4 py-1.5 text-sm text-neutral-600 hover:bg-neutral-200 transition-colors"
                @click="cancelReview"
              >
                取消
              </button>
              <button
                :class="[
                  'rounded px-4 py-1.5 text-sm font-medium text-white transition-colors',
                  reviewAction === 'approve'
                    ? 'bg-green-600 hover:bg-green-700'
                    : 'bg-red-600 hover:bg-red-700',
                ]"
                :disabled="reviewAction === 'reject' && !rejectReason.trim()"
                @click="confirmReview"
              >
                确认
              </button>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Reprocess dialog -->
      <Transition name="dialog-fade">
        <div
          v-if="reprocessDialogOpen"
          class="fixed inset-0 z-50 flex items-center justify-center"
          @click.self="cancelReprocess"
        >
          <div class="absolute inset-0 bg-black/40" />
          <div class="relative w-full max-w-md rounded-lg bg-white shadow-xl">
            <div class="px-6 py-4 border-b border-neutral-200">
              <h3 class="text-base font-semibold text-neutral-900">重新采购</h3>
            </div>
            <div class="px-6 py-4">
              <p class="text-sm text-neutral-600">
                确认重新发起采购流程？订单
                <span class="font-mono text-neutral-800">{{ reprocessOrderId }}</span>
              </p>
            </div>
            <div class="flex justify-end gap-2 px-6 py-4 border-t border-neutral-100 bg-neutral-50/50 rounded-b-lg">
              <button
                class="rounded px-4 py-1.5 text-sm text-neutral-600 hover:bg-neutral-200 transition-colors"
                @click="cancelReprocess"
              >
                取消
              </button>
              <button
                class="rounded px-4 py-1.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                @click="confirmReprocess"
              >
                确认
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease-out;
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
