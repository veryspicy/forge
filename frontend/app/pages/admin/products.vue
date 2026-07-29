<script setup lang="ts">
import {
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  getSuppliers,
  probeProducts,
  uploadProductImage,
} from "~/composables/useAdminApi";

definePageMeta({
  layout: "admin",
  middleware: "auth",
});

// ──────────────────────── Types ────────────────────────

interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  price: number;
  cost_price?: number;
  stock: number;
  status: "draft" | "active" | "inactive";
  description?: string;
  supplier_id?: string;
  supplier_name?: string;
  image_url?: string;
}

interface ProductForm {
  name: string;
  sku: string;
  category: string;
  description: string;
  cost_price: number | null;
  price: number | null;
  stock: number;
  supplier_id: string;
  status: "draft" | "active";
  images: string[];
}

interface SupplierOption {
  id: string;
  name: string;
}

const statusLabels: Record<string, string> = {
  draft: "草稿",
  active: "在售",
  inactive: "下架",
};

const statusColors: Record<string, string> = {
  draft: "oklch(0.55 0.01 145)",
  active: "oklch(0.55 0.15 160)",
  inactive: "oklch(0.50 0.04 85)",
};

const categories = [
  "狗狗用品",
  "猫咪用品",
  "水族用品",
  "鸟类用品",
  "小宠用品",
  "宠物食品",
  "宠物医疗",
  "宠物玩具",
  "宠物服饰",
];

// ──────────────────────── Table config ────────────────────────

const columns = [
  { key: "name", label: "商品名", sortable: true },
  { key: "sku", label: "SKU", sortable: true },
  { key: "category", label: "分类", sortable: true },
  { key: "price", label: "价格", sortable: true, align: "right" as const },
  { key: "stock", label: "库存", sortable: true, align: "right" as const },
  { key: "status", label: "状态", sortable: false },
  { key: "actions", label: "操作", sortable: false, width: "140px" },
];

// ──────────────────────── State ────────────────────────

const loading = ref(false);
const products = ref<Product[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);

const searchQuery = ref("");
const selectedCategory = ref("");
const selectedStatus = ref("");

const selectedIds = ref<string[]>([]);

const showDrawer = ref(false);
const drawerMode = ref<"create" | "edit">("create");
const editingId = ref<string | null>(null);
const formLoading = ref(false);

const uploadingImage = ref(false);

const showProbeDialog = ref(false);
const probeLoading = ref(false);
const probeResults = ref<any[]>([]);
const probeKeyword = ref("");
const probePetType = ref("全部");
const probeMaxPrice = ref<number | null>(null);

const suppliers = ref<SupplierOption[]>([]);

const emptyForm = (): ProductForm => ({
  name: "",
  sku: "",
  category: categories[0],
  description: "",
  cost_price: null,
  price: null,
  stock: 0,
  supplier_id: "",
  status: "draft",
  images: [],
});

const form = ref<ProductForm>(emptyForm());

// ──────────────────────── Computed ────────────────────────

const hasSelection = computed(() => selectedIds.value.length > 0);

// ──────────────────────── Data loading ────────────────────────

let searchTimer: ReturnType<typeof setTimeout> | null = null;

async function loadProducts() {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      limit: 20,
    };
    if (searchQuery.value) params.search = searchQuery.value;
    if (selectedCategory.value) params.category = selectedCategory.value;
    if (selectedStatus.value) params.status = selectedStatus.value;

    const data: any = await getProducts(params);
    products.value = data?.items ?? data?.products ?? data?.results ?? [];
    totalPages.value = data?.totalPages ?? data?.total_pages ?? data?.pages ?? 1;
  } catch {
    products.value = [];
  } finally {
    loading.value = false;
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage.value = 1;
    loadProducts();
  }, 300);
}

function onFilterChange() {
  currentPage.value = 1;
  selectedIds.value = [];
  loadProducts();
}

function onPageChange(page: number) {
  currentPage.value = page;
  selectedIds.value = [];
  loadProducts();
}

async function loadSuppliers() {
  try {
    const data: any = await getSuppliers({ limit: 200 });
    suppliers.value = (data?.items ?? data?.suppliers ?? data?.results ?? []).map(
      (s: any) => ({ id: s.id ?? s._id, name: s.name ?? s.company_name ?? "" })
    );
  } catch {
    suppliers.value = [];
  }
}

// ──────────────────────── Product CRUD ────────────────────────

function openCreateDrawer() {
  drawerMode.value = "create";
  editingId.value = null;
  form.value = emptyForm();
  showDrawer.value = true;
}

function openEditDrawer(product: Product) {
  drawerMode.value = "edit";
  editingId.value = product.id;
  form.value = {
    name: product.name,
    sku: product.sku,
    category: product.category,
    description: product.description ?? "",
    cost_price: product.cost_price ?? null,
    price: product.price,
    stock: product.stock,
    supplier_id: product.supplier_id ?? "",
    status: product.status === "inactive" ? "draft" : product.status,
    images: (product as any).images ?? (product.image_url ? [product.image_url] : []),
  };
  showDrawer.value = true;
}

function closeDrawer() {
  showDrawer.value = false;
  formLoading.value = false;
}

async function handleSave() {
  if (!form.value.name || !form.value.sku) return;

  formLoading.value = true;
  try {
    const payload: Record<string, any> = {
      name: form.value.name,
      sku: form.value.sku,
      category: form.value.category,
      description: form.value.description,
      cost_price: form.value.cost_price,
      price: form.value.price,
      stock: form.value.stock,
      supplier_id: form.value.supplier_id || undefined,
      status: form.value.status,
      images: form.value.images,
    };

    if (drawerMode.value === "create") {
      await createProduct(payload);
    } else if (editingId.value) {
      await updateProduct(editingId.value, payload);
    }

    closeDrawer();
    loadProducts();
  } catch {
    // error handled by useAdminApi interceptor
  } finally {
    formLoading.value = false;
  }
}

async function handleImageUpload(e: Event) {
  const target = e.target as HTMLInputElement;
  const files = target.files;
  if (!files || files.length === 0 || !editingId.value) return;

  uploadingImage.value = true;
  for (const file of Array.from(files)) {
    try {
      const res: any = await uploadProductImage(editingId.value, file);
      form.value.images.push(res.url);
    } catch {
      // handled by interceptor
    }
  }
  uploadingImage.value = false;
  target.value = "";
}

function removeFormImage(idx: number) {
  form.value.images.splice(idx, 1);
}

async function handleDelete(product: Product) {
  if (!confirm(`确定删除商品「${product.name}」？此操作不可撤销。`)) return;
  try {
    await deleteProduct(product.id);
    loadProducts();
  } catch {
    // error handled by interceptor
  }
}

async function handleDeactivate(product: Product) {
  try {
    await updateProduct(product.id, { status: "inactive" });
    loadProducts();
  } catch {
    // handled
  }
}

async function batchDeactivate() {
  if (!confirm(`确定下架选中的 ${selectedIds.value.length} 个商品？`)) return;
  try {
    await Promise.all(selectedIds.value.map((id) => updateProduct(id, { status: "inactive" })));
    selectedIds.value = [];
    loadProducts();
  } catch {
    // handled
  }
}

async function batchDelete() {
  if (!confirm(`确定删除选中的 ${selectedIds.value.length} 个商品？此操作不可撤销。`)) return;
  try {
    await Promise.all(selectedIds.value.map((id) => deleteProduct(id)));
    selectedIds.value = [];
    loadProducts();
  } catch {
    // handled
  }
}

// ──────────────────────── AI Probe ────────────────────────

const petTypes = ["全部", "狗狗", "猫咪", "水族", "鸟类", "小宠"];

function openProbeDialog() {
  probeKeyword.value = "";
  probePetType.value = "全部";
  probeMaxPrice.value = null;
  probeResults.value = [];
  showProbeDialog.value = true;
}

async function handleProbe() {
  if (!probeKeyword.value.trim()) return;
  probeLoading.value = true;
  try {
    const data: any = await probeProducts({
      keyword: probeKeyword.value,
      pet_type: probePetType.value,
      max_price: probeMaxPrice.value,
    });
    probeResults.value = data?.results ?? data?.items ?? data ?? [];
  } catch {
    probeResults.value = [];
  } finally {
    probeLoading.value = false;
  }
}

// ──────────────────────── Utilities ────────────────────────

function formatPrice(val: number): string {
  return `¥${val.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ──────────────────────── Lifecycle ────────────────────────

onMounted(() => {
  loadProducts();
  loadSuppliers();
});
</script>

<template>
  <div class="space-y-5">
    <!-- Page header -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-2xl font-heading font-bold tracking-tight text-neutral-900">
          商品管理
        </h1>
        <p class="mt-0.5 text-sm text-neutral-500">
          共 {{ products.length }} 件商品
        </p>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center gap-3">
      <!-- Search -->
      <div class="relative flex-1 min-w-[200px] max-w-[320px]">
        <svg
          class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-neutral-400 pointer-events-none"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索商品名或SKU..."
          class="w-full rounded border border-neutral-200 bg-white py-2 pl-9 pr-3 text-sm text-neutral-700 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
          @input="onSearchInput"
        />
      </div>

      <!-- Category filter -->
      <select
        v-model="selectedCategory"
        class="rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
        @change="onFilterChange"
      >
        <option value="">全部分类</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>

      <!-- Status filter -->
      <select
        v-model="selectedStatus"
        class="rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
        @change="onFilterChange"
      >
        <option value="">全部状态</option>
        <option value="active">在售</option>
        <option value="draft">草稿</option>
        <option value="inactive">下架</option>
      </select>

      <div class="flex-1" />

      <!-- Action buttons -->
      <button
        class="inline-flex items-center gap-2 rounded bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 active:bg-accent-700"
        @click="openCreateDrawer"
      >
        <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        新建商品
      </button>

      <button
        class="inline-flex items-center gap-2 rounded border border-accent-200 bg-accent-50 px-4 py-2 text-sm font-medium text-accent-700 transition-colors hover:bg-accent-100 active:bg-accent-200"
        @click="openProbeDialog"
      >
        <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.5 5.25-3 7.5-1 1.5-2 3-2 3.5s-1 2-2 2-2-.5-2-2-1-2-2-3.5c-1.5-2.25-3-5-3-7.5a7 7 0 0 1 7-7z" />
          <line x1="12" y1="11" x2="12" y2="15" />
          <circle cx="12" cy="8" r="1" />
        </svg>
        AI探针
      </button>
    </div>

    <!-- Batch action bar -->
    <div
      v-if="hasSelection"
      class="flex items-center gap-3 rounded border border-accent-200 bg-accent-50/60 px-4 py-2.5 animate-fade-in"
    >
      <span class="text-sm font-medium text-accent-800">
        已选择 {{ selectedIds.length }} 项
      </span>
      <span class="w-px h-5 bg-accent-200" />
      <button
        class="rounded px-3 py-1 text-sm text-accent-700 transition-colors hover:bg-accent-100"
        @click="batchDeactivate"
      >
        批量下架
      </button>
      <button
        class="rounded px-3 py-1 text-sm text-error transition-colors hover:bg-red-50"
        @click="batchDelete"
      >
        批量删除
      </button>
      <span class="flex-1" />
      <button
        class="rounded px-2 py-1 text-sm text-neutral-500 transition-colors hover:text-neutral-700"
        @click="selectedIds = []"
      >
        取消选择
      </button>
    </div>

    <!-- Product table -->
    <DataTable
      :columns="columns"
      :data="products"
      :loading="loading"
      :selectable="true"
      :selected="selectedIds"
      :current-page="currentPage"
      :total-pages="totalPages"
      @update:selected="selectedIds = $event"
      @page-change="onPageChange"
    >
      <!-- Product name -->
      <template #name="{ row }">
        <div class="flex items-center gap-3">
          <div
            class="size-9 rounded bg-neutral-100 flex items-center justify-center shrink-0 overflow-hidden"
          >
            <img
              v-if="row.image_url"
              :src="row.image_url"
              :alt="row.name"
              class="size-full object-cover"
            />
            <svg
              v-else
              class="size-5 text-neutral-300"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </div>
          <span class="font-medium text-neutral-800 text-sm truncate max-w-[180px]">
            {{ row.name }}
          </span>
        </div>
      </template>

      <!-- SKU -->
      <template #sku="{ value }">
        <span class="font-mono text-xs text-neutral-500">{{ value }}</span>
      </template>

      <!-- Category -->
      <template #category="{ value }">
        <span class="text-sm text-neutral-600">{{ value }}</span>
      </template>

      <!-- Price -->
      <template #price="{ value }">
        <span class="tabular-nums font-medium text-neutral-800">
          {{ formatPrice(Number(value)) }}
        </span>
      </template>

      <!-- Stock -->
      <template #stock="{ value }">
        <span
          :class="[
            'tabular-nums text-sm font-medium',
            Number(value) <= 0
              ? 'text-error'
              : Number(value) <= 10
                ? 'text-warning'
                : 'text-neutral-700',
          ]"
        >
          {{ value }}
        </span>
      </template>

      <!-- Status -->
      <template #status="{ row }">
        <span class="inline-flex items-center gap-1.5 text-xs font-medium">
          <span
            class="inline-block size-2 rounded-full shrink-0"
            :style="{ backgroundColor: statusColors[row.status] ?? 'oklch(0.55 0.00 145)' }"
          />
          {{ statusLabels[row.status] ?? row.status }}
        </span>
      </template>

      <!-- Actions -->
      <template #actions="{ row }">
        <div class="flex items-center gap-px">
          <button
            class="rounded px-2 py-1 text-xs text-accent-600 transition-colors hover:bg-accent-50 hover:text-accent-700"
            @click="openEditDrawer(row as Product)"
          >
            编辑
          </button>
          <span class="w-px h-4 bg-neutral-200" />
          <button
            v-if="row.status === 'active'"
            class="rounded px-2 py-1 text-xs text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            @click="handleDeactivate(row as Product)"
          >
            下架
          </button>
          <span v-if="row.status === 'active'" class="w-px h-4 bg-neutral-200" />
          <button
            class="rounded px-2 py-1 text-xs text-error/80 transition-colors hover:bg-red-50 hover:text-error"
            @click="handleDelete(row as Product)"
          >
            删除
          </button>
        </div>
      </template>
    </DataTable>

    <!-- Empty state (when not loading and no data) -->
    <div
      v-if="!loading && products.length === 0"
      class="flex flex-col items-center justify-center py-20 text-center"
    >
      <svg
        class="size-16 text-neutral-200 mb-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1"
      >
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </svg>
      <p class="text-sm text-neutral-400">
        暂无商品，点击新建商品开始添加
      </p>
      <button
        class="mt-4 text-sm font-medium text-accent-600 hover:text-accent-700 transition-colors"
        @click="openCreateDrawer"
      >
        新建商品
      </button>
    </div>

    <!-- ════════════════ Create/Edit Drawer ════════════════ -->

    <Transition name="drawer">
      <div
        v-if="showDrawer"
        class="fixed inset-0 z-50 flex justify-end"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/30"
          @click="closeDrawer"
        />

        <!-- Drawer panel -->
        <div class="relative w-full max-w-[600px] bg-white shadow-xl flex flex-col animate-slide-in-right">
          <!-- Header -->
          <div class="flex items-center justify-between shrink-0 border-b border-neutral-200 px-6 py-4">
            <h2 class="text-lg font-heading font-semibold text-neutral-900">
              {{ drawerMode === "create" ? "新建商品" : "编辑商品" }}
            </h2>
            <button
              class="rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              @click="closeDrawer"
            >
              <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- Form body -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            <!-- Name -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">
                商品名称 <span class="text-error">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                placeholder="输入商品名称"
                class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
              />
            </div>

            <!-- SKU + Category row -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">
                  SKU <span class="text-error">*</span>
                </label>
                <input
                  v-model="form.sku"
                  type="text"
                  placeholder="SKU编码"
                  class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 font-mono"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">分类</label>
                <select
                  v-model="form.category"
                  class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                >
                  <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>
            </div>

            <!-- Description -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">描述</label>
              <textarea
                v-model="form.description"
                rows="3"
                placeholder="商品描述..."
                class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15 resize-none"
              />
            </div>

            <!-- Price rows -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">成本价</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-neutral-400">¥</span>
                  <input
                    v-model.number="form.cost_price"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    class="w-full rounded border border-neutral-200 bg-white py-2 pl-7 pr-3 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                  />
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">售价</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-neutral-400">¥</span>
                  <input
                    v-model.number="form.price"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    class="w-full rounded border border-neutral-200 bg-white py-2 pl-7 pr-3 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                  />
                </div>
              </div>
            </div>

            <!-- Stock + Supplier row -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">库存数量</label>
                <input
                  v-model.number="form.stock"
                  type="number"
                  min="0"
                  class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">供应商</label>
                <select
                  v-model="form.supplier_id"
                  class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                >
                  <option value="">未选择</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
            </div>

            <!-- Image upload -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">商品图片</label>
              <!-- Existing images -->
              <div v-if="form.images.length > 0" class="flex flex-wrap gap-2 mb-3">
                <div
                  v-for="(img, idx) in form.images"
                  :key="idx"
                  class="relative size-20 rounded border border-neutral-200 overflow-hidden shrink-0"
                >
                  <img :src="img" :alt="'Image ' + (idx + 1)" class="size-full object-cover" />
                  <button
                    class="absolute top-0.5 right-0.5 size-5 rounded-full bg-black/50 text-white flex items-center justify-center text-xs leading-none hover:bg-red-500/80 transition-colors"
                    @click="removeFormImage(idx)"
                  >&times;</button>
                </div>
              </div>
              <!-- Upload button (edit mode only) -->
              <template v-if="drawerMode === 'edit'">
                <label class="inline-flex items-center gap-2 rounded border-2 border-dashed border-neutral-200 px-4 py-6 text-sm text-neutral-400 transition-colors hover:border-neutral-300 hover:text-neutral-500 cursor-pointer w-full justify-center"
                  :class="{ 'opacity-50 pointer-events-none': uploadingImage }">
                  <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                  <span>{{ uploadingImage ? '上传中...' : '拖拽或点击上传图片 (JPG/PNG/WebP/SVG)' }}</span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml,image/bmp"
                    multiple
                    class="hidden"
                    :disabled="uploadingImage"
                    @change="handleImageUpload"
                  />
                </label>
              </template>
              <div v-else class="rounded border-2 border-dashed border-neutral-200 py-8 text-center text-sm text-neutral-400">
                保存产品后可在编辑页面上传图片
              </div>
            </div>

            <!-- Status -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 mb-1.5">状态</label>
              <div class="flex gap-3">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    v-model="form.status"
                    type="radio"
                    value="draft"
                    class="size-3.5 accent-accent-500"
                  />
                  <span class="text-sm text-neutral-600">草稿</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    v-model="form.status"
                    type="radio"
                    value="active"
                    class="size-3.5 accent-accent-500"
                  />
                  <span class="text-sm text-neutral-600">在售</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-end gap-3 shrink-0 border-t border-neutral-200 px-6 py-4">
            <button
              class="rounded border border-neutral-200 bg-white px-5 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
              @click="closeDrawer"
            >
              取消
            </button>
            <button
              :disabled="!form.name || !form.sku || formLoading"
              class="rounded bg-accent-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 active:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleSave"
            >
              {{ formLoading ? "保存中..." : "保存" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ════════════════ AI Probe Dialog ════════════════ -->

    <Transition name="modal">
      <div
        v-if="showProbeDialog"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/30"
          @click="showProbeDialog = false"
        />

        <!-- Dialog -->
        <div class="relative w-full max-w-[600px] mx-4 bg-white rounded shadow-xl animate-scale-in overflow-hidden">
          <!-- Header -->
          <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
            <h2 class="text-lg font-heading font-semibold text-neutral-900">AI探针 - 自动探测商品</h2>
            <button
              class="rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              @click="showProbeDialog = false"
            >
              <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- Form -->
          <div class="px-6 py-5 space-y-4">
            <div class="grid grid-cols-3 gap-3">
              <div class="col-span-3 sm:col-span-1">
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">搜索关键词</label>
                <input
                  v-model="probeKeyword"
                  type="text"
                  placeholder="如：狗粮、猫砂"
                  class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                  @keyup.enter="handleProbe"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">宠物类型</label>
                <select
                  v-model="probePetType"
                  class="w-full rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                >
                  <option v-for="pt in petTypes" :key="pt" :value="pt">{{ pt }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-neutral-700 mb-1.5">最高价格</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-neutral-400">¥</span>
                  <input
                    v-model.number="probeMaxPrice"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="不限"
                    class="w-full rounded border border-neutral-200 bg-white py-2 pl-7 pr-3 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-accent-400 focus:ring-2 focus:ring-accent-400/15"
                  />
                </div>
              </div>
            </div>

            <button
              :disabled="!probeKeyword.trim() || probeLoading"
              class="inline-flex items-center gap-2 rounded bg-accent-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 active:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleProbe"
            >
              <svg
                v-if="probeLoading"
                class="size-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25" />
                <path d="M12 2a10 10 0 0 1 10 10" stroke-opacity="1" />
              </svg>
              <svg
                v-else
                class="size-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.5 5.25-3 7.5-1 1.5-2 3-2 3.5s-1 2-2 2-2-.5-2-2-1-2-2-3.5c-1.5-2.25-3-5-3-7.5a7 7 0 0 1 7-7z" />
                <line x1="12" y1="11" x2="12" y2="15" />
                <circle cx="12" cy="8" r="1" />
              </svg>
              {{ probeLoading ? "探测中..." : "开始探测" }}
            </button>
          </div>

          <!-- Results -->
          <div v-if="probeResults.length > 0" class="border-t border-neutral-200 px-6 py-4">
            <h3 class="text-sm font-semibold text-neutral-700 mb-3">
              探测结果 ({{ probeResults.length }} 条)
            </h3>
            <div class="max-h-[320px] overflow-y-auto space-y-2">
              <div
                v-for="(item, idx) in probeResults"
                :key="idx"
                class="flex items-center gap-3 rounded border border-neutral-100 bg-neutral-50/50 px-4 py-3"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-800 truncate">{{ item.name ?? item.product_name }}</p>
                  <p class="text-xs text-neutral-500 mt-0.5">
                    {{ item.supplier ?? item.supplier_name ?? "未知供应商" }}
                  </p>
                </div>
                <span class="tabular-nums text-sm font-medium text-neutral-700 shrink-0">
                  {{ item.price ? formatPrice(Number(item.price)) : "-" }}
                </span>
                <span
                  :class="[
                    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium shrink-0',
                    Number(item.match_score ?? item.confidence ?? 0) >= 0.7
                      ? 'bg-success/10 text-success'
                      : Number(item.match_score ?? item.confidence ?? 0) >= 0.4
                        ? 'bg-warning/10 text-warning'
                        : 'bg-neutral-100 text-neutral-500',
                  ]"
                >
                  {{ ((Number(item.match_score ?? item.confidence ?? 0)) * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </div>

          <!-- Empty results -->
          <div
            v-if="!probeLoading && probeResults.length === 0 && probeKeyword && probeKeyword.trim()"
            class="border-t border-neutral-200 px-6 py-10 text-center"
          >
            <p class="text-sm text-neutral-400">未找到匹配结果，尝试调整关键词</p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Drawer transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.25s ease-out-expo;
}
.drawer-enter-active > div:nth-child(2),
.drawer-leave-active > div:nth-child(2) {
  transition: transform 0.25s ease-out-expo;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from > div:nth-child(2) {
  transform: translateX(100%);
}
.drawer-leave-to > div:nth-child(2) {
  transform: translateX(100%);
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease-out-expo;
}
.modal-enter-active > div:nth-child(2),
.modal-leave-active > div:nth-child(2) {
  transition: transform 0.2s ease-out-expo, opacity 0.2s ease-out-expo;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from > div:nth-child(2) {
  transform: scale(0.95);
  opacity: 0;
}
.modal-leave-to > div:nth-child(2) {
  transform: scale(0.95);
  opacity: 0;
}
</style>
