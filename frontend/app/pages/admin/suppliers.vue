<script setup lang="ts">
import {
  getSuppliers,
  createSupplier,
  deactivateSupplier,
} from "~/composables/useAdminApi";

definePageMeta({
  layout: "admin",
  middleware: "auth",
});

// ──────────────────────── Types ────────────────────────

interface Supplier {
  id: string;
  name: string;
  type: "api" | "manual";
  api_status?: "connected" | "error" | "unconfigured";
  api_base_url?: string;
  supply_regions?: string[];
  product_count?: number;
  status: "active" | "inactive";
  notes?: string;
  headers?: { key: string; value: string }[];
}

interface SupplierForm {
  name: string;
  type: "api";
  api_base_url: string;
  api_key: string;
  headers: { key: string; value: string }[];
  supply_regions: string[];
  notes: string;
}

interface ShopProduct {
  id: string;
  name: string;
  sku: string;
}

interface SupplierProduct {
  id: string;
  name: string;
  sku: string;
  price: number;
}

interface SkuMapping {
  shopSku: string;
  shopName: string;
  supplierSku: string;
  supplierName: string;
}

const ALL_REGIONS = ["中国", "东南亚", "中东", "欧洲", "北美", "日韩", "全球"];

const columns = [
  { key: "name", label: "供应商名称", sortable: true },
  { key: "type", label: "类型", sortable: true },
  { key: "api_status", label: "API连接状态", sortable: false },
  { key: "supply_regions", label: "供货区域", sortable: false },
  { key: "product_count", label: "商品数", sortable: true, align: "right" as const },
  { key: "status", label: "状态", sortable: true },
  { key: "actions", label: "操作", sortable: false, width: "180px" },
];

// ──────────────────────── State ────────────────────────

const loading = ref(false);
const suppliers = ref<Supplier[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);

const searchQuery = ref("");
const statusFilter = ref<"all" | "active" | "inactive">("all");

const showDialog = ref(false);
const dialogMode = ref<"create" | "edit">("create");
const editingId = ref<string | null>(null);
const formLoading = ref(false);

const showSkuDialog = ref(false);
const skuSupplier = ref<Supplier | null>(null);
const skuMode = ref<"view" | "edit">("view");
const shopProducts = ref<ShopProduct[]>([]);
const supplierProducts = ref<SupplierProduct[]>([]);
const skuMappings = ref<SkuMapping[]>([]);
const shopSearchQuery = ref("");
const supplierSearchQuery = ref("");
const skuLoading = ref(false);

const emptyForm = (): SupplierForm => ({
  name: "",
  type: "api",
  api_base_url: "",
  api_key: "",
  headers: [],
  supply_regions: [],
  notes: "",
});

const form = ref<SupplierForm>(emptyForm());

// ──────────────────────── Data loading ────────────────────────

let searchTimer: ReturnType<typeof setTimeout> | null = null;

async function loadSuppliers() {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      limit: 20,
    };
    if (searchQuery.value) params.search = searchQuery.value;
    if (statusFilter.value !== "all") params.status = statusFilter.value;

    const data: any = await getSuppliers(params);
    suppliers.value = (data?.items ?? data?.suppliers ?? data?.results ?? []).map(
      (s: any) => ({
        id: s.id ?? s._id,
        name: s.name ?? s.company_name ?? "",
        type: s.type ?? "manual",
        api_status: s.api_status ?? (s.type === "api" ? "unconfigured" : undefined),
        api_base_url: s.api_base_url,
        supply_regions: s.supply_regions ?? [],
        product_count: s.product_count ?? 0,
        status: s.status ?? "active",
        notes: s.notes,
        headers: s.headers ?? [],
      })
    );
    totalPages.value = data?.totalPages ?? data?.total_pages ?? data?.pages ?? 1;
  } catch {
    suppliers.value = [];
  } finally {
    loading.value = false;
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage.value = 1;
    loadSuppliers();
  }, 300);
}

function onStatusFilterChange() {
  currentPage.value = 1;
  loadSuppliers();
}

function onPageChange(page: number) {
  currentPage.value = page;
  loadSuppliers();
}

// ──────────────────────── Supplier CRUD ────────────────────────

function openCreateDialog() {
  dialogMode.value = "create";
  editingId.value = null;
  form.value = emptyForm();
  showDialog.value = true;
}

function openEditDialog(supplier: Supplier) {
  dialogMode.value = "edit";
  editingId.value = supplier.id;
  form.value = {
    name: supplier.name,
    type: "api",
    api_base_url: supplier.api_base_url ?? "",
    api_key: "",
    headers: supplier.headers?.length
      ? [...supplier.headers.map((h) => ({ ...h }))]
      : [],
    supply_regions: [...(supplier.supply_regions ?? [])],
    notes: supplier.notes ?? "",
  };
  showDialog.value = true;
}

function closeDialog() {
  showDialog.value = false;
  formLoading.value = false;
}

async function handleSave() {
  if (!form.value.name) return;

  formLoading.value = true;
  try {
    const payload: Record<string, any> = {
      name: form.value.name,
      type: form.value.type,
      api_base_url: form.value.api_base_url || undefined,
      api_key: form.value.api_key || undefined,
      headers: form.value.headers.filter((h) => h.key.trim()),
      supply_regions: form.value.supply_regions,
      notes: form.value.notes || undefined,
      status: "active",
    };

    if (dialogMode.value === "create") {
      await createSupplier(payload);
    } else if (editingId.value) {
      // For editing, only send changed fields
      await createSupplier({ ...payload, id: editingId.value });
    }

    closeDialog();
    loadSuppliers();
  } catch {
    // error handled by useAdminApi interceptor
  } finally {
    formLoading.value = false;
  }
}

async function handleDeactivate(supplier: Supplier) {
  try {
    await deactivateSupplier(supplier.id);
    loadSuppliers();
  } catch {
    // error handled by interceptor
  }
}

// ──────────────────────── Form helpers ────────────────────────

function addHeaderRow() {
  form.value.headers.push({ key: "", value: "" });
}

function removeHeaderRow(index: number) {
  form.value.headers.splice(index, 1);
}

function toggleRegion(region: string) {
  const idx = form.value.supply_regions.indexOf(region);
  if (idx >= 0) {
    form.value.supply_regions.splice(idx, 1);
  } else {
    form.value.supply_regions.push(region);
  }
}

// ──────────────────────── SKU Mapping ────────────────────────

function openSkuMapping(supplier: Supplier) {
  skuSupplier.value = supplier;
  skuMode.value = "view";
  shopSearchQuery.value = "";
  supplierSearchQuery.value = "";
  loadSkuData();
  showSkuDialog.value = true;
}

async function loadSkuData() {
  skuLoading.value = true;
  try {
    // Simulated data — replace with actual API calls when available
    const { getProducts } = await import("~/composables/useAdminApi");
    const productData: any = await getProducts({ limit: 100 });
    shopProducts.value = (productData?.items ?? productData?.products ?? productData?.results ?? []).map(
      (p: any) => ({
        id: p.id ?? p._id,
        name: p.name ?? "",
        sku: p.sku ?? "",
      })
    );

    // Supplier products — using mock data until supplier product sync API is ready
    supplierProducts.value = [
      { id: "sp1", name: "Premium Dog Food 5kg", sku: "SP-DF-001", price: 89 },
      { id: "sp2", name: "Cat Litter Box XL", sku: "SP-CL-002", price: 120 },
      { id: "sp3", name: "Bird Cage Deluxe", sku: "SP-BC-003", price: 350 },
      { id: "sp4", name: "Fish Tank Filter", sku: "SP-FT-004", price: 45 },
    ];

    skuMappings.value = [
      {
        shopSku: "PET-DF-001",
        shopName: "天然狗粮 5kg",
        supplierSku: "SP-DF-001",
        supplierName: "Premium Dog Food 5kg",
      },
      {
        shopSku: "PET-CL-002",
        shopName: "特大号猫砂盆",
        supplierSku: "SP-CL-002",
        supplierName: "Cat Litter Box XL",
      },
    ];
  } catch {
    shopProducts.value = [];
    supplierProducts.value = [];
    skuMappings.value = [];
  } finally {
    skuLoading.value = false;
  }
}

function closeSkuDialog() {
  showSkuDialog.value = false;
}

function addMapping(shopProduct: ShopProduct, supplierProduct: SupplierProduct) {
  const exists = skuMappings.value.some(
    (m) => m.shopSku === shopProduct.sku && m.supplierSku === supplierProduct.sku
  );
  if (exists) return;
  skuMappings.value.push({
    shopSku: shopProduct.sku,
    shopName: shopProduct.name,
    supplierSku: supplierProduct.sku,
    supplierName: supplierProduct.name,
  });
}

function removeMapping(index: number) {
  skuMappings.value.splice(index, 1);
}

// ──────────────────────── Helpers ────────────────────────

function getApiStatusLabel(status?: string): string {
  switch (status) {
    case "connected":
      return "连接正常";
    case "error":
      return "连接异常";
    case "unconfigured":
    default:
      return "未配置";
  }
}

function getApiStatusColor(status?: string): string {
  switch (status) {
    case "connected":
      return "oklch(0.55 0.15 160)";
    case "error":
      return "oklch(0.52 0.18 25)";
    case "unconfigured":
    default:
      return "oklch(0.55 0.01 145)";
  }
}

const filteredShopProducts = computed(() => {
  if (!shopSearchQuery.value) return shopProducts.value;
  const q = shopSearchQuery.value.toLowerCase();
  return shopProducts.value.filter(
    (p) =>
      p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
  );
});

const filteredSupplierProducts = computed(() => {
  if (!supplierSearchQuery.value) return supplierProducts.value;
  const q = supplierSearchQuery.value.toLowerCase();
  return supplierProducts.value.filter(
    (p) =>
      p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
  );
});

// ──────────────────────── Init ────────────────────────

onMounted(() => {
  loadSuppliers();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- ════════════════ Page Header ════════════════ -->
    <div class="shrink-0 px-6 pt-6 pb-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-heading font-bold text-neutral-900">供应商管理</h1>
          <p class="mt-0.5 text-sm text-neutral-500">
            管理 API 供应商接入与 SKU 映射关系
          </p>
        </div>
        <button
          class="inline-flex items-center gap-1.5 rounded bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 active:bg-accent-700"
          @click="openCreateDialog"
        >
          <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          添加供应商
        </button>
      </div>
    </div>

    <!-- ════════════════ Toolbar ════════════════ -->
    <div class="shrink-0 px-6 pb-4 flex items-center gap-3">
      <!-- Search -->
      <div class="relative flex-1 max-w-[320px]">
        <svg
          class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-neutral-400 pointer-events-none"
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
          placeholder="搜索供应商名称..."
          class="w-full rounded border border-neutral-200 bg-white py-2 pl-9 pr-3 text-sm text-neutral-700 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
          @input="onSearchInput"
        />
      </div>

      <!-- Status filter -->
      <div class="flex items-center rounded border border-neutral-200 overflow-hidden">
        <button
          v-for="opt in [
            { value: 'all', label: '全部' },
            { value: 'active', label: '活跃' },
            { value: 'inactive', label: '已停用' },
          ]"
          :key="opt.value"
          class="px-3 py-2 text-sm transition-colors"
          :class="
            statusFilter === opt.value
              ? 'bg-accent-50 text-accent-700 font-medium'
              : 'text-neutral-600 hover:bg-neutral-50'
          "
          @click="statusFilter = opt.value as any; onStatusFilterChange()"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- ════════════════ Data Table ════════════════ -->
    <div class="flex-1 px-6 pb-6 min-h-0">
      <DataTable
        :columns="columns"
        :data="suppliers"
        :loading="loading"
        :current-page="currentPage"
        :total-pages="totalPages"
        @page-change="onPageChange"
      >
        <!-- Type column -->
        <template #type="{ row }">
          <span
            v-if="row.type === 'api'"
            class="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium"
            style="color: oklch(0.50 0.12 250)"
          >
            API
          </span>
          <span
            v-else
            class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-500"
          >
            手动
          </span>
        </template>

        <!-- API status column -->
        <template #api_status="{ row }">
          <span v-if="row.type === 'api'" class="inline-flex items-center gap-1.5 text-xs">
            <span
              class="inline-block size-2 rounded-full shrink-0"
              :style="{ backgroundColor: getApiStatusColor(row.api_status) }"
            />
            {{ getApiStatusLabel(row.api_status) }}
          </span>
          <span v-else class="text-xs text-neutral-400">—</span>
        </template>

        <!-- Supply regions column -->
        <template #supply_regions="{ row }">
          <div v-if="row.supply_regions?.length" class="flex flex-wrap gap-1">
            <span
              v-for="region in row.supply_regions"
              :key="region"
              class="inline-flex items-center rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600"
            >
              {{ region }}
            </span>
          </div>
          <span v-else class="text-xs text-neutral-400">—</span>
        </template>

        <!-- Product count column -->
        <template #product_count="{ row }">
          <span class="tabular-nums">{{ row.product_count ?? 0 }}</span>
        </template>

        <!-- Status column -->
        <template #status="{ row }">
          <span
            v-if="row.status === 'active'"
            class="inline-flex items-center gap-1.5 text-xs font-medium"
          >
            <span class="inline-block size-2 rounded-full shrink-0" style="background-color: oklch(0.55 0.15 160)" />
            活跃
          </span>
          <span v-else class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400">
            <span class="inline-block size-2 rounded-full shrink-0" style="background-color: oklch(0.55 0.01 145)" />
            已停用
          </span>
        </template>

        <!-- Actions column -->
        <template #actions="{ row }">
          <div class="flex items-center gap-1">
            <button
              class="rounded px-2 py-1 text-xs text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
              @click="openEditDialog(row as Supplier)"
            >
              编辑
            </button>
            <span class="w-px h-4 bg-neutral-200" />
            <button
              class="rounded px-2 py-1 text-xs text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
              @click="openSkuMapping(row as Supplier)"
            >
              SKU映射
            </button>
            <span v-if="row.status === 'active'" class="w-px h-4 bg-neutral-200" />
            <button
              v-if="row.status === 'active'"
              class="rounded px-2 py-1 text-xs text-error/80 transition-colors hover:bg-red-50 hover:text-error"
              @click="handleDeactivate(row as Supplier)"
            >
              停用
            </button>
          </div>
        </template>
      </DataTable>

      <!-- Empty state -->
      <div
        v-if="!loading && suppliers.length === 0"
        class="flex flex-col items-center justify-center py-20 text-center"
      >
        <svg
          class="size-16 text-neutral-200 mb-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1"
        >
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
        <p class="text-sm text-neutral-400">暂无供应商，点击添加供应商开始接入</p>
        <button
          class="mt-4 text-sm font-medium text-accent-600 hover:text-accent-700 transition-colors"
          @click="openCreateDialog"
        >
          添加供应商
        </button>
      </div>
    </div>

    <!-- ════════════════ Add/Edit Supplier Dialog ════════════════ -->

    <Transition name="drawer">
      <div v-if="showDialog" class="fixed inset-0 z-50 flex justify-end">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30" @click="closeDialog" />

        <!-- Drawer panel -->
        <div
          class="relative w-full max-w-[620px] bg-white shadow-xl flex flex-col animate-slide-in-right"
        >
          <!-- Header -->
          <div class="flex items-center justify-between shrink-0 border-b border-neutral-200 px-6 py-4">
            <h2 class="text-lg font-heading font-semibold text-neutral-900">
              {{ dialogMode === "create" ? "添加供应商" : "编辑供应商" }}
            </h2>
            <button
              class="rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              @click="closeDialog"
            >
              <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- Form body -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            <!-- Supplier Name -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">
                供应商名称 <span class="text-error">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                placeholder="输入供应商名称"
                class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
              />
            </div>

            <!-- Type -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">
                类型 <span class="text-error">*</span>
              </label>
              <div class="flex gap-3">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    v-model="form.type"
                    type="radio"
                    value="api"
                    class="size-3.5 accent-accent-500"
                  />
                  <span class="text-sm text-neutral-700 font-medium">API供应商</span>
                  <span class="text-xs text-neutral-400">通过API自动同步商品</span>
                </label>
              </div>
            </div>

            <!-- API Configuration Card -->
            <div class="rounded border border-neutral-200 bg-neutral-50/50 overflow-hidden">
              <div class="border-b border-neutral-200 bg-neutral-100/70 px-4 py-2.5">
                <h3 class="text-sm font-medium text-neutral-700">API配置</h3>
              </div>
              <div class="px-4 py-4 space-y-4">
                <!-- API Base URL -->
                <div>
                  <label class="block text-sm font-medium text-neutral-600 mb-1.5">API Base URL</label>
                  <input
                    v-model="form.api_base_url"
                    type="url"
                    placeholder="https://api.supplier.com/v1"
                    class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 font-mono"
                  />
                </div>

                <!-- API Key -->
                <div>
                  <label class="block text-sm font-medium text-neutral-600 mb-1.5">
                    API Key
                    <span v-if="dialogMode === 'edit'" class="text-xs text-neutral-400 font-normal">
                      (创建后不可查看，留空表示不修改)
                    </span>
                  </label>
                  <input
                    v-model="form.api_key"
                    type="password"
                    placeholder="输入API密钥"
                    class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 font-mono"
                  />
                </div>

                <!-- Custom Headers -->
                <div>
                  <div class="flex items-center justify-between mb-1.5">
                    <label class="text-sm font-medium text-neutral-600">请求头自定义</label>
                    <button
                      class="text-xs text-accent-600 hover:text-accent-700 transition-colors font-medium"
                      @click="addHeaderRow"
                    >
                      + 添加请求头
                    </button>
                  </div>
                  <div v-if="form.headers.length === 0" class="text-xs text-neutral-400 py-1">
                    无需自定义请求头
                  </div>
                  <div v-for="(header, index) in form.headers" :key="index" class="flex items-center gap-2 mb-2">
                    <input
                      v-model="header.key"
                      type="text"
                      placeholder="Header名"
                      class="flex-1 rounded border border-neutral-200 bg-white px-2.5 py-1.5 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 font-mono"
                    />
                    <input
                      v-model="header.value"
                      type="text"
                      placeholder="值"
                      class="flex-1 rounded border border-neutral-200 bg-white px-2.5 py-1.5 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 font-mono"
                    />
                    <button
                      class="rounded p-1 text-neutral-400 hover:text-error transition-colors shrink-0"
                      @click="removeHeaderRow(index)"
                    >
                      <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Supply Regions -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-2">供货区域</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="region in ALL_REGIONS"
                  :key="region"
                  class="rounded border px-3 py-1.5 text-sm transition-colors"
                  :class="
                    form.supply_regions.includes(region)
                      ? 'border-accent-400 bg-accent-50 text-accent-700'
                      : 'border-neutral-200 text-neutral-600 hover:border-neutral-300 hover:bg-neutral-50'
                  "
                  @click="toggleRegion(region)"
                >
                  {{ region }}
                </button>
              </div>
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">备注</label>
              <textarea
                v-model="form.notes"
                rows="3"
                placeholder="供应商备注信息..."
                class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 resize-none"
              />
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end gap-3 shrink-0 border-t border-neutral-200 px-6 py-4">
            <button
              class="rounded border border-neutral-200 bg-white px-5 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
              @click="closeDialog"
            >
              取消
            </button>
            <button
              :disabled="!form.name || formLoading"
              class="rounded bg-accent-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 active:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleSave"
            >
              {{ formLoading ? "保存中..." : "保存" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ════════════════ SKU Mapping Dialog ════════════════ -->

    <Transition name="modal">
      <div
        v-if="showSkuDialog"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30" @click="closeSkuDialog" />

        <!-- Dialog -->
        <div class="relative w-full max-w-[1024px] mx-4 max-h-[90vh] bg-white rounded shadow-xl animate-scale-in overflow-hidden flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between shrink-0 border-b border-neutral-200 px-6 py-4">
            <h2 class="text-lg font-heading font-semibold text-neutral-900">
              SKU映射 — {{ skuSupplier?.name }}
            </h2>
            <button
              class="rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              @click="closeSkuDialog"
            >
              <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- SKU mapping content -->
          <div class="flex-1 overflow-hidden flex flex-col min-h-0">
            <!-- Loading -->
            <div v-if="skuLoading" class="flex items-center justify-center py-20">
              <div class="space-y-2 w-full max-w-md px-8">
                <div v-for="i in 5" :key="i" class="h-4 rounded bg-neutral-100 animate-pulse" />
              </div>
            </div>

            <template v-else>
              <!-- Mapping list (existing mappings) -->
              <div v-if="skuMappings.length > 0" class="shrink-0 px-6 py-3 border-b border-neutral-100">
                <h3 class="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">
                  已建立映射 ({{ skuMappings.length }})
                </h3>
                <div class="space-y-1">
                  <div
                    v-for="(mapping, idx) in skuMappings"
                    :key="idx"
                    class="flex items-center gap-3 text-sm py-1.5"
                  >
                    <div class="flex-1 flex items-center gap-2 min-w-0">
                      <span class="shrink-0 rounded bg-neutral-100 px-1.5 py-0.5 text-xs font-mono text-neutral-600">
                        {{ mapping.shopSku }}
                      </span>
                      <span class="truncate text-neutral-700">{{ mapping.shopName }}</span>
                    </div>
                    <svg class="size-4 text-neutral-300 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                    <div class="flex-1 flex items-center gap-2 min-w-0">
                      <span class="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-xs font-mono" style="color: oklch(0.50 0.12 250)">
                        {{ mapping.supplierSku }}
                      </span>
                      <span class="truncate text-neutral-700">{{ mapping.supplierName }}</span>
                    </div>
                    <button
                      class="rounded p-0.5 text-neutral-300 hover:text-error transition-colors shrink-0"
                      @click="removeMapping(idx)"
                    >
                      <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Dual panel: Shop Products vs Supplier Products -->
              <div class="flex-1 flex min-h-0 overflow-hidden">
                <!-- Left panel: Shop Products -->
                <div class="flex-1 flex flex-col min-w-0 border-r border-neutral-200">
                  <div class="shrink-0 px-4 py-2.5 border-b border-neutral-100">
                    <h3 class="text-sm font-medium text-neutral-700">本店商品</h3>
                    <div class="relative mt-1.5">
                      <svg
                        class="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-neutral-400 pointer-events-none"
                        viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      >
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                      </svg>
                      <input
                        v-model="shopSearchQuery"
                        type="text"
                        placeholder="搜索..."
                        class="w-full rounded border border-neutral-200 bg-white py-1.5 pl-7 pr-2.5 text-xs text-neutral-700 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400"
                      />
                    </div>
                  </div>
                  <div class="flex-1 overflow-y-auto">
                    <div
                      v-for="product in filteredShopProducts"
                      :key="product.id"
                      class="flex items-center justify-between px-4 py-2 border-b border-neutral-50 hover:bg-neutral-50/60 transition-colors cursor-pointer"
                      @click="skuMode === 'edit' && addMapping(product, supplierProducts[0])"
                    >
                      <div class="min-w-0">
                        <p class="text-sm text-neutral-700 truncate">{{ product.name }}</p>
                        <p class="text-xs text-neutral-400 font-mono">{{ product.sku }}</p>
                      </div>
                      <span
                        v-if="skuMappings.some((m) => m.shopSku === product.sku)"
                        class="shrink-0 text-xs text-green-600 ml-2"
                      >
                        已映射
                      </span>
                    </div>
                    <div
                      v-if="filteredShopProducts.length === 0"
                      class="px-4 py-8 text-center text-xs text-neutral-400"
                    >
                      暂无商品
                    </div>
                  </div>
                </div>

                <!-- Divider with arrow indicators -->
                <div class="flex flex-col items-center justify-center gap-2 px-2 shrink-0">
                  <div
                    v-for="mapping in skuMappings.slice(0, 5)"
                    :key="mapping.shopSku"
                    class="flex items-center"
                  >
                    <div
                      class="w-8 h-px"
                      style="background-color: oklch(0.70 0.007 145)"
                    />
                    <div class="size-1.5 rounded-full" style="background-color: oklch(0.82 0.007 145)" />
                  </div>
                </div>

                <!-- Right panel: Supplier Products -->
                <div class="flex-1 flex flex-col min-w-0">
                  <div class="shrink-0 px-4 py-2.5 border-b border-neutral-100">
                    <h3 class="text-sm font-medium text-neutral-700">供应商商品</h3>
                    <div class="relative mt-1.5">
                      <svg
                        class="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-neutral-400 pointer-events-none"
                        viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      >
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                      </svg>
                      <input
                        v-model="supplierSearchQuery"
                        type="text"
                        placeholder="搜索..."
                        class="w-full rounded border border-neutral-200 bg-white py-1.5 pl-7 pr-2.5 text-xs text-neutral-700 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400"
                      />
                    </div>
                  </div>
                  <div class="flex-1 overflow-y-auto">
                    <div
                      v-for="product in filteredSupplierProducts"
                      :key="product.id"
                      class="flex items-center justify-between px-4 py-2 border-b border-neutral-50 hover:bg-neutral-50/60 transition-colors"
                    >
                      <div class="min-w-0">
                        <p class="text-sm text-neutral-700 truncate">{{ product.name }}</p>
                        <p class="text-xs text-neutral-400 font-mono">{{ product.sku }}</p>
                      </div>
                      <span v-if="product.price" class="shrink-0 text-xs text-neutral-500 ml-2 tabular-nums">
                        &yen;{{ product.price }}
                      </span>
                    </div>
                    <div
                      v-if="filteredSupplierProducts.length === 0"
                      class="px-4 py-8 text-center text-xs text-neutral-400"
                    >
                      暂无供应商商品
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-between shrink-0 border-t border-neutral-200 px-6 py-3">
            <p class="text-xs text-neutral-400">
              共 {{ skuMappings.length }} 个映射关系
            </p>
            <div class="flex items-center gap-2">
              <button
                class="rounded border border-neutral-200 bg-white px-4 py-1.5 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
                @click="closeSkuDialog"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
