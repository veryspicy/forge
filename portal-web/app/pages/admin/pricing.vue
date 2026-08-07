<script setup lang="ts">
import {
  getPricingRules,
  createPricingRule,
  createPromotion,
} from "~/composables/useAdminApi";
import { cn } from "~/utils/cn";

definePageMeta({
  layout: "admin",
  middleware: "auth",
});

// ──────────────────────── Types ────────────────────────

interface RegionalRule {
  id: string;
  region: string;
  multiplier: number;
  shipping_fee: number;
  priority: number;
  enabled: boolean;
}

interface Promotion {
  id: string;
  name: string;
  type: "THRESHOLD_DISCOUNT" | "COUPON" | "MEMBER_PRICE";
  discount_value: number;
  discount_type?: "fixed" | "percentage";
  threshold_amount?: number;
  reduce_amount?: number;
  coupon_code?: string;
  min_spend?: number;
  start_date: string;
  end_date: string;
  stackable: boolean;
  scope: "all" | "products" | "categories";
  enabled: boolean;
}

const regionLabels: Record<string, string> = {
  CN: "中国",
  SEA: "东南亚",
  ME: "中东",
  EU: "欧洲",
  NA: "北美",
  JP_KR: "日韩",
  GLOBAL: "全球",
};

const regionOptions = Object.entries(regionLabels).map(([value, label]) => ({
  value,
  label,
}));

const typeLabels: Record<string, string> = {
  THRESHOLD_DISCOUNT: "满减",
  COUPON: "优惠券",
  MEMBER_PRICE: "会员价",
};

const typeColors: Record<string, string> = {
  THRESHOLD_DISCOUNT: "oklch(0.65 0.16 85)",
  COUPON: "oklch(0.50 0.12 250)",
  MEMBER_PRICE: "oklch(0.45 0.12 300)",
};

const typeBgColors: Record<string, string> = {
  THRESHOLD_DISCOUNT: "oklch(0.96 0.04 85 / 0.55)",
  COUPON: "oklch(0.94 0.04 250 / 0.50)",
  MEMBER_PRICE: "oklch(0.94 0.06 300 / 0.40)",
};

// ──────────────────────── State ────────────────────────

const activeTab = ref<"global" | "regional" | "promotions">("global");
const loading = ref(false);

// Global formula
const globalMultiplier = ref(1.3);
const globalShipping = ref(15.0);
const previewCost = ref(100);
const globalSaving = ref(false);
const globalSaved = ref(false);

// Regional rules
const regionalRules = ref<RegionalRule[]>([]);
const showRegionalModal = ref(false);
const editingRule = ref<RegionalRule | null>(null);
const regionalForm = ref({
  region: "CN",
  multiplier: 1.2,
  shipping_fee: 20,
  priority: 10,
  enabled: true,
});
const dragIndex = ref<number | null>(null);
const dragOverIndex = ref<number | null>(null);

// Promotions
const promotions = ref<Promotion[]>([]);
const showPromoModal = ref(false);
const editingPromo = ref<Promotion | null>(null);
const promoForm = ref({
  name: "",
  type: "THRESHOLD_DISCOUNT" as Promotion["type"],
  threshold_amount: 200,
  reduce_amount: 30,
  coupon_code: "",
  discount_type: "fixed" as "fixed" | "percentage",
  discount_value: 10,
  min_spend: 0,
  start_date: "",
  end_date: "",
  stackable: false,
  scope: "all" as "all" | "products" | "categories",
  enabled: true,
});

// ──────────────────────── Computed ────────────────────────

const previewPrice = computed(() => {
  const raw = previewCost.value * globalMultiplier.value + globalShipping.value;
  return raw.toFixed(2);
});

const regionColumns = [
  { key: "priority", label: "优先级", sortable: true, align: "center" as const, width: "60px" },
  { key: "region", label: "区域", sortable: true },
  { key: "multiplier", label: "倍率", sortable: true, align: "right" as const },
  { key: "shipping_fee", label: "固定运费", sortable: true, align: "right" as const },
  { key: "enabled", label: "状态", sortable: false, align: "center" as const, width: "80px" },
  { key: "actions", label: "操作", sortable: false, align: "center" as const, width: "120px" },
];

const promoColumns = [
  { key: "name", label: "名称", sortable: true },
  { key: "type", label: "类型", sortable: false },
  { key: "discount_info", label: "折扣详情", sortable: false },
  { key: "period", label: "有效期", sortable: false },
  { key: "stackable", label: "叠加", sortable: false, align: "center" as const, width: "60px" },
  { key: "scope", label: "适用商品", sortable: false },
  { key: "enabled", label: "状态", sortable: false, align: "center" as const, width: "80px" },
  { key: "actions", label: "操作", sortable: false, align: "center" as const, width: "120px" },
];

const scopeLabels: Record<string, string> = {
  all: "全部商品",
  products: "指定商品",
  categories: "指定分类",
};

function promoDiscountInfo(p: Promotion): string {
  if (p.type === "THRESHOLD_DISCOUNT") {
    return `满 ${p.threshold_amount} 减 ${p.reduce_amount}`;
  }
  if (p.type === "COUPON") {
    const prefix = p.discount_type === "fixed" ? "¥" : "";
    const suffix = p.discount_type === "fixed" ? "" : "%";
    const min = p.min_spend ? ` (最低消费 ¥${p.min_spend})` : "";
    return `${p.coupon_code || "-"} ${prefix}${p.discount_value}${suffix}${min}`;
  }
  return `会员价 ¥${p.discount_value}`;
}

// ──────────────────────── Data Fetching ────────────────────────

async function fetchRules() {
  loading.value = true;
  try {
    const res = (await getPricingRules()) as any;
    regionalRules.value = (res.rules ?? res.data ?? []).map((r: any, i: number) => ({
      id: r.id ?? String(i),
      region: r.region ?? "CN",
      multiplier: r.multiplier ?? 1.0,
      shipping_fee: r.shipping_fee ?? 0,
      priority: r.priority ?? i * 10,
      enabled: r.enabled ?? r.is_active ?? true,
    }));
    promotions.value = (res.promotions ?? []).map((p: any, i: number) => ({
      id: p.id ?? String(i),
      name: p.name ?? "",
      type: p.type ?? "THRESHOLD_DISCOUNT",
      discount_value: p.discount_value ?? 0,
      discount_type: p.discount_type,
      threshold_amount: p.threshold_amount,
      reduce_amount: p.reduce_amount,
      coupon_code: p.coupon_code,
      min_spend: p.min_spend,
      start_date: p.start_date ?? "",
      end_date: p.end_date ?? "",
      stackable: p.stackable ?? false,
      scope: p.scope ?? "all",
      enabled: p.enabled ?? p.is_active ?? true,
    }));
    if (res.global_multiplier != null) globalMultiplier.value = res.global_multiplier;
    if (res.global_shipping != null) globalShipping.value = res.global_shipping;
  } catch {
    // Use local state if API unavailable
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchRules();
});

// ──────────────────────── Tab 1: Global Formula ────────────────────────

async function saveGlobal() {
  globalSaving.value = true;
  try {
    await createPricingRule({
      type: "global",
      multiplier: globalMultiplier.value,
      shipping_fee: globalShipping.value,
    });
    globalSaved.value = true;
    setTimeout(() => {
      globalSaved.value = false;
    }, 2000);
  } catch {
    // Silently handle
  } finally {
    globalSaving.value = false;
  }
}

// ──────────────────────── Tab 2: Regional Rules ────────────────────────

function openRegionalModal(rule?: RegionalRule) {
  if (rule) {
    editingRule.value = rule;
    regionalForm.value = {
      region: rule.region,
      multiplier: rule.multiplier,
      shipping_fee: rule.shipping_fee,
      priority: rule.priority,
      enabled: rule.enabled,
    };
  } else {
    editingRule.value = null;
    const maxPriority = regionalRules.value.reduce((max, r) => Math.max(max, r.priority), 0);
    regionalForm.value = {
      region: "CN",
      multiplier: 1.2,
      shipping_fee: 20,
      priority: maxPriority + 10,
      enabled: true,
    };
  }
  showRegionalModal.value = true;
}

function closeRegionalModal() {
  showRegionalModal.value = false;
  editingRule.value = null;
}

async function saveRegionalRule() {
  try {
    const payload = {
      region: regionalForm.value.region,
      multiplier: regionalForm.value.multiplier,
      shipping_fee: regionalForm.value.shipping_fee,
      priority: regionalForm.value.priority,
      enabled: regionalForm.value.enabled,
    };
    if (editingRule.value) {
      await createPricingRule({ ...payload, id: editingRule.value.id, _action: "update" });
      const idx = regionalRules.value.findIndex((r) => r.id === editingRule.value!.id);
      if (idx >= 0) {
        regionalRules.value[idx] = { ...regionalRules.value[idx], ...payload };
      }
    } else {
      const res = (await createPricingRule(payload)) as any;
      const newId = res.id ?? `rule-${Date.now()}`;
      regionalRules.value.push({ id: newId, ...payload });
    }
    closeRegionalModal();
  } catch {
    // Silently handle
  }
}

function removeRegionalRule(rule: RegionalRule) {
  regionalRules.value = regionalRules.value.filter((r) => r.id !== rule.id);
}

function toggleRegionalRule(rule: RegionalRule) {
  rule.enabled = !rule.enabled;
}

// Drag to reorder
function onDragStart(idx: number) {
  dragIndex.value = idx;
}

function onDragOver(e: DragEvent, idx: number) {
  e.preventDefault();
  dragOverIndex.value = idx;
}

function onDragEnd() {
  if (dragIndex.value != null && dragOverIndex.value != null && dragIndex.value !== dragOverIndex.value) {
    const items = [...regionalRules.value];
    const [moved] = items.splice(dragIndex.value, 1);
    items.splice(dragOverIndex.value, 0, moved);
    items.forEach((r, i) => {
      r.priority = i * 10;
    });
    regionalRules.value = items;
  }
  dragIndex.value = null;
  dragOverIndex.value = null;
}

// ──────────────────────── Tab 3: Promotions ────────────────────────

function openPromoModal(promo?: Promotion) {
  if (promo) {
    editingPromo.value = promo;
    promoForm.value = {
      name: promo.name,
      type: promo.type,
      threshold_amount: promo.threshold_amount ?? 200,
      reduce_amount: promo.reduce_amount ?? 30,
      coupon_code: promo.coupon_code ?? "",
      discount_type: promo.discount_type ?? "fixed",
      discount_value: promo.discount_value,
      min_spend: promo.min_spend ?? 0,
      start_date: promo.start_date,
      end_date: promo.end_date,
      stackable: promo.stackable,
      scope: promo.scope,
      enabled: promo.enabled,
    };
  } else {
    editingPromo.value = null;
    promoForm.value = {
      name: "",
      type: "THRESHOLD_DISCOUNT",
      threshold_amount: 200,
      reduce_amount: 30,
      coupon_code: "",
      discount_type: "fixed",
      discount_value: 10,
      min_spend: 0,
      start_date: "",
      end_date: "",
      stackable: false,
      scope: "all",
      enabled: true,
    };
  }
  showPromoModal.value = true;
}

function closePromoModal() {
  showPromoModal.value = false;
  editingPromo.value = null;
}

async function savePromotion() {
  try {
    const payload: any = {
      name: promoForm.value.name,
      type: promoForm.value.type,
      stackable: promoForm.value.stackable,
      scope: promoForm.value.scope,
      enabled: promoForm.value.enabled,
      start_date: promoForm.value.start_date || undefined,
      end_date: promoForm.value.end_date || undefined,
    };
    if (promoForm.value.type === "THRESHOLD_DISCOUNT") {
      payload.threshold_amount = promoForm.value.threshold_amount;
      payload.reduce_amount = promoForm.value.reduce_amount;
    } else if (promoForm.value.type === "COUPON") {
      payload.coupon_code = promoForm.value.coupon_code;
      payload.discount_type = promoForm.value.discount_type;
      payload.discount_value = promoForm.value.discount_value;
      payload.min_spend = promoForm.value.min_spend || undefined;
    } else {
      payload.discount_value = promoForm.value.discount_value;
    }

    if (editingPromo.value) {
      await createPromotion({ ...payload, id: editingPromo.value.id, _action: "update" });
      const idx = promotions.value.findIndex((p) => p.id === editingPromo.value!.id);
      if (idx >= 0) {
        promotions.value[idx] = { ...promotions.value[idx], ...payload };
      }
    } else {
      const res = (await createPromotion(payload)) as any;
      const newId = res.id ?? `promo-${Date.now()}`;
      promotions.value.push({
        id: newId,
        ...payload,
        discount_value: payload.discount_value ?? 0,
        start_date: payload.start_date ?? "",
        end_date: payload.end_date ?? "",
      });
    }
    closePromoModal();
  } catch {
    // Silently handle
  }
}

function removePromotion(promo: Promotion) {
  promotions.value = promotions.value.filter((p) => p.id !== promo.id);
}

function togglePromotion(promo: Promotion) {
  promo.enabled = !promo.enabled;
}

// ──────────────────────── Tabs config ────────────────────────

const tabs = [
  { key: "global" as const, label: "全局定价公式" },
  { key: "regional" as const, label: "区域差异化定价" },
  { key: "promotions" as const, label: "促销活动管理" },
];
</script>

<template>
  <div class="animate-fade-in">
    <!-- Page header -->
    <div class="mb-6">
      <h2 class="text-xl font-heading font-bold text-neutral-900">定价引擎</h2>
      <p class="mt-0.5 text-sm text-neutral-500">配置定价公式、区域规则和促销活动</p>
    </div>

    <!-- Tabs -->
    <div class="mb-6 flex gap-1 rounded-lg bg-neutral-100 p-1 w-fit">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="cn(
          'px-4 py-2 text-sm font-medium rounded-md transition-all duration-200',
          activeTab === tab.key
            ? 'bg-white text-neutral-900 shadow-sm'
            : 'text-neutral-500 hover:text-neutral-700'
        )"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- ──────────────── Tab 1: Global Pricing Formula ──────────────── -->
    <div v-if="activeTab === 'global'" class="space-y-6 animate-slide-up">
      <!-- Formula display -->
      <div class="rounded-lg border border-primary-200 bg-primary-50/40 px-6 py-5">
        <div class="text-center">
          <p class="text-xs font-medium uppercase tracking-wide text-primary-600 mb-2">当前定价公式</p>
          <p class="text-3xl font-heading font-bold text-neutral-900 tabular-nums tracking-tight">
            售价 = 成本价 &times; <span class="text-accent-600">{{ globalMultiplier }}</span> + <span class="text-accent-600">{{ globalShipping.toFixed(2) }}</span>
          </p>
          <p class="mt-1 text-sm text-neutral-500">倍率 &times; 成本价 + 固定运费（元）</p>
        </div>
      </div>

      <!-- Controls -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Left: inputs -->
        <div class="rounded-lg border border-neutral-200 bg-white px-6 py-5 space-y-5">
          <h3 class="text-sm font-semibold text-neutral-800">公式参数</h3>

          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">倍率</label>
            <div class="relative">
              <input
                v-model.number="globalMultiplier"
                type="number"
                step="0.01"
                min="0.1"
                class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
              />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-neutral-400">&times;</span>
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">固定运费（元）</label>
            <div class="relative">
              <input
                v-model.number="globalShipping"
                type="number"
                step="0.01"
                min="0"
                class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
              />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-neutral-400">+</span>
            </div>
          </div>

          <button
            :disabled="globalSaving"
            class="w-full rounded-md bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            @click="saveGlobal"
          >
            <span v-if="globalSaving" class="inline-flex items-center gap-2">
              <span class="size-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              保存中...
            </span>
            <span v-else-if="globalSaved" class="inline-flex items-center gap-1.5">
              <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12" /></svg>
              已保存
            </span>
            <span v-else>保存公式</span>
          </button>
        </div>

        <!-- Right: preview -->
        <div class="rounded-lg border border-neutral-200 bg-white px-6 py-5 space-y-5">
          <h3 class="text-sm font-semibold text-neutral-800">实时价格预览</h3>

          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">成本价（元）</label>
            <input
              v-model.number="previewCost"
              type="number"
              step="0.01"
              min="0"
              class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
            />
          </div>

          <div class="rounded-md bg-neutral-50 border border-neutral-100 px-4 py-4">
            <div class="flex items-baseline justify-between">
              <span class="text-xs font-medium text-neutral-500">计算售价</span>
              <Transition
                name="price"
                mode="out-in"
              >
                <span
                  :key="previewPrice"
                  class="text-3xl font-heading font-bold text-accent-600 tabular-nums"
                >
                  {{ previewPrice }}
                </span>
              </Transition>
            </div>
            <div class="mt-2 space-y-1 text-xs text-neutral-400">
              <p>成本价 {{ previewCost.toFixed(2) }} &times; 倍率 {{ globalMultiplier }} = {{ (previewCost * globalMultiplier).toFixed(2) }}</p>
              <p>+ 固定运费 {{ globalShipping.toFixed(2) }} = <span class="font-medium text-neutral-700">{{ previewPrice }}</span></p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ──────────────── Tab 2: Regional Differential Pricing ──────────────── -->
    <div v-if="activeTab === 'regional'" class="space-y-4 animate-slide-up">
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-500">
          共 {{ regionalRules.length }} 条规则，拖拽调整优先级（数值越小优先级越高）
        </p>
        <button
          class="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 active:bg-primary-800 transition-colors"
          @click="openRegionalModal()"
        >
          <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          添加规则
        </button>
      </div>

      <!-- Rules table with drag -->
      <div class="overflow-hidden rounded border border-neutral-200 bg-white">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50 text-left">
              <th class="w-8 px-2 py-2.5" />
              <th
                v-for="col in regionColumns"
                :key="col.key"
                :class="[
                  'px-4 py-2.5 font-medium text-neutral-600',
                  (col.align as string) === 'right' && 'text-right',
                  (col.align as string) === 'center' && 'text-center',
                ]"
                :style="col.width ? { width: col.width } : {}"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="regionalRules.length === 0">
              <td :colspan="regionColumns.length + 1" class="px-4 py-16 text-center text-sm text-neutral-400">
                暂无区域定价规则，点击"添加规则"开始配置
              </td>
            </tr>
            <tr
              v-for="(rule, ri) in regionalRules"
              :key="rule.id"
              :class="cn(
                'border-b border-neutral-100 transition-colors hover:bg-neutral-50/60 cursor-grab active:cursor-grabbing',
                dragIndex === ri && 'opacity-40',
                dragOverIndex === ri && dragIndex !== ri && 'bg-primary-50'
              )"
              draggable="true"
              @dragstart="onDragStart(ri)"
              @dragover="(e) => onDragOver(e as DragEvent, ri)"
              @dragend="onDragEnd"
            >
              <td class="px-2 py-2.5 text-neutral-300">
                <svg class="size-4" viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="5" r="1.5" /><circle cx="15" cy="5" r="1.5" /><circle cx="9" cy="12" r="1.5" /><circle cx="15" cy="12" r="1.5" /><circle cx="9" cy="19" r="1.5" /><circle cx="15" cy="19" r="1.5" /></svg>
              </td>
              <td class="px-4 py-2.5 text-center text-xs font-medium tabular-nums text-neutral-500">
                {{ rule.priority }}
              </td>
              <td class="px-4 py-2.5">
                <span class="inline-flex items-center gap-1.5">
                  <span
                    class="inline-block size-2 rounded-full shrink-0"
                    :style="{ backgroundColor: typeColors.THRESHOLD_DISCOUNT }"
                  />
                  {{ regionLabels[rule.region] ?? rule.region }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-right tabular-nums text-neutral-700">
                {{ rule.multiplier.toFixed(2) }}
              </td>
              <td class="px-4 py-2.5 text-right tabular-nums text-neutral-700">
                {{ rule.shipping_fee.toFixed(2) }}
              </td>
              <td class="px-4 py-2.5 text-center">
                <button
                  :class="cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition',
                    rule.enabled
                      ? 'bg-success/15 text-success'
                      : 'bg-neutral-100 text-neutral-400'
                  )"
                  @click="toggleRegionalRule(rule)"
                >
                  <span class="size-1.5 rounded-full" :class="rule.enabled ? 'bg-success' : 'bg-neutral-400'" />
                  {{ rule.enabled ? "启用" : "禁用" }}
                </button>
              </td>
              <td class="px-4 py-2.5 text-center">
                <div class="flex items-center justify-center gap-2">
                  <button
                    class="rounded p-1 text-neutral-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                    @click="openRegionalModal(rule)"
                  >
                    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  </button>
                  <button
                    class="rounded p-1 text-neutral-400 hover:text-error hover:bg-error/10 transition-colors"
                    @click="removeRegionalRule(rule)"
                  >
                    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ──────────────── Tab 3: Promotions ──────────────── -->
    <div v-if="activeTab === 'promotions'" class="space-y-4 animate-slide-up">
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-500">共 {{ promotions.length }} 个促销活动</p>
        <button
          class="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 active:bg-primary-800 transition-colors"
          @click="openPromoModal()"
        >
          <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          添加促销
        </button>
      </div>

      <!-- Promo table -->
      <div class="overflow-hidden rounded border border-neutral-200 bg-white">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50 text-left">
              <th
                v-for="col in promoColumns"
                :key="col.key"
                :class="[
                  'px-4 py-2.5 font-medium text-neutral-600',
                  (col.align as string) === 'right' && 'text-right',
                  (col.align as string) === 'center' && 'text-center',
                ]"
                :style="col.width ? { width: col.width } : {}"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="promotions.length === 0">
              <td :colspan="promoColumns.length" class="px-4 py-16 text-center text-sm text-neutral-400">
                暂无促销活动，点击"添加促销"开始创建
              </td>
            </tr>
            <tr
              v-for="promo in promotions"
              :key="promo.id"
              class="border-b border-neutral-100 transition-colors hover:bg-neutral-50/60"
            >
              <td class="px-4 py-2.5 font-medium text-neutral-800">
                {{ promo.name }}
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :style="{
                    backgroundColor: typeBgColors[promo.type],
                    color: typeColors[promo.type],
                  }"
                >
                  <span
                    class="size-1.5 rounded-full shrink-0"
                    :style="{ backgroundColor: typeColors[promo.type] }"
                  />
                  {{ typeLabels[promo.type] }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-neutral-600 text-xs font-mono">
                {{ promoDiscountInfo(promo) }}
              </td>
              <td class="px-4 py-2.5 text-xs text-neutral-500">
                <template v-if="promo.start_date && promo.end_date">
                  {{ promo.start_date }} ~ {{ promo.end_date }}
                </template>
                <span v-else class="text-neutral-300">-</span>
              </td>
              <td class="px-4 py-2.5 text-center">
                <span
                  :class="cn(
                    'text-xs font-medium',
                    promo.stackable ? 'text-success' : 'text-neutral-400'
                  )"
                >
                  {{ promo.stackable ? "可叠加" : "不可" }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-xs text-neutral-500">
                {{ scopeLabels[promo.scope] ?? promo.scope }}
              </td>
              <td class="px-4 py-2.5 text-center">
                <button
                  :class="cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition',
                    promo.enabled
                      ? 'bg-success/15 text-success'
                      : 'bg-neutral-100 text-neutral-400'
                  )"
                  @click="togglePromotion(promo)"
                >
                  <span class="size-1.5 rounded-full" :class="promo.enabled ? 'bg-success' : 'bg-neutral-400'" />
                  {{ promo.enabled ? "启用" : "禁用" }}
                </button>
              </td>
              <td class="px-4 py-2.5 text-center">
                <div class="flex items-center justify-center gap-2">
                  <button
                    class="rounded p-1 text-neutral-400 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                    @click="openPromoModal(promo)"
                  >
                    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  </button>
                  <button
                    class="rounded p-1 text-neutral-400 hover:text-error hover:bg-error/10 transition-colors"
                    @click="removePromotion(promo)"
                  >
                    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ──────────────── Priority Explanation Card ──────────────── -->
    <div class="mt-8 rounded-lg border border-secondary-100 bg-secondary-50/30 px-5 py-4">
      <h4 class="text-xs font-semibold uppercase tracking-wide text-secondary-700 mb-3">定价优先级</h4>
      <div class="space-y-2">
        <div class="flex items-center gap-3 pl-0">
          <span class="flex items-center justify-center size-5 rounded bg-accent-500 text-white text-[10px] font-bold shrink-0">1</span>
          <span class="text-sm font-semibold text-accent-700">手动覆盖价</span>
          <span class="text-xs text-neutral-400 ml-auto">最高优先级</span>
        </div>
        <div class="flex items-center gap-3 pl-6">
          <span class="flex items-center justify-center size-5 rounded bg-secondary-500 text-white text-[10px] font-bold shrink-0">2</span>
          <span class="text-sm font-medium text-secondary-700">促销折扣</span>
        </div>
        <div class="flex items-center gap-3 pl-12">
          <span class="flex items-center justify-center size-5 rounded bg-primary-500 text-white text-[10px] font-bold shrink-0">3</span>
          <span class="text-sm text-primary-700">区域定价公式</span>
        </div>
        <div class="flex items-center gap-3 pl-18">
          <span class="flex items-center justify-center size-5 rounded bg-neutral-400 text-white text-[10px] font-bold shrink-0">4</span>
          <span class="text-sm text-neutral-500">全局默认公式</span>
          <span class="text-xs text-neutral-400 ml-auto">最低优先级</span>
        </div>
      </div>
      <p class="mt-3 text-xs text-neutral-400 leading-relaxed">
        定价计算时，系统按以上顺序逐级查找匹配规则。若上一级规则覆盖了某商品，则不再应用下级规则。
      </p>
    </div>

    <!-- ──────────────── Regional Rule Modal ──────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showRegionalModal"
          class="fixed inset-0 z-50 flex items-center justify-center"
        >
          <div class="absolute inset-0 bg-black/40" @click="closeRegionalModal" />
          <div class="relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl animate-scale-in">
            <h3 class="text-lg font-heading font-semibold text-neutral-900 mb-5">
              {{ editingRule ? "编辑区域规则" : "添加区域规则" }}
            </h3>

            <div class="space-y-4">
              <div>
                <label class="block text-xs font-medium text-neutral-500 mb-1.5">区域</label>
                <select
                  v-model="regionalForm.region"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                >
                  <option v-for="opt in regionOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-xs font-medium text-neutral-500 mb-1.5">倍率</label>
                <input
                  v-model.number="regionalForm.multiplier"
                  type="number"
                  step="0.01"
                  min="0.1"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                />
              </div>

              <div>
                <label class="block text-xs font-medium text-neutral-500 mb-1.5">固定运费</label>
                <input
                  v-model.number="regionalForm.shipping_fee"
                  type="number"
                  step="0.01"
                  min="0"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                />
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">优先级</label>
                  <input
                    v-model.number="regionalForm.priority"
                    type="number"
                    min="0"
                    class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">状态</label>
                  <div class="flex items-center gap-3 pt-1">
                    <label class="inline-flex items-center gap-1.5 text-sm text-neutral-700 cursor-pointer">
                      <input
                        v-model="regionalForm.enabled"
                        type="radio"
                        :value="true"
                        class="text-primary-500 focus:ring-primary-400"
                      />
                      启用
                    </label>
                    <label class="inline-flex items-center gap-1.5 text-sm text-neutral-700 cursor-pointer">
                      <input
                        v-model="regionalForm.enabled"
                        type="radio"
                        :value="false"
                        class="text-neutral-400"
                      />
                      禁用
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div class="mt-6 flex justify-end gap-2">
              <button
                class="rounded-md border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
                @click="closeRegionalModal"
              >
                取消
              </button>
              <button
                class="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 active:bg-primary-800 transition-colors"
                @click="saveRegionalRule"
              >
                {{ editingRule ? "保存修改" : "添加规则" }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ──────────────── Promotion Modal ──────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showPromoModal"
          class="fixed inset-0 z-50 flex items-center justify-center"
        >
          <div class="absolute inset-0 bg-black/40" @click="closePromoModal" />
          <div class="relative w-full max-w-lg rounded-lg bg-white p-6 shadow-xl animate-scale-in max-h-[90vh] overflow-y-auto">
            <h3 class="text-lg font-heading font-semibold text-neutral-900 mb-5">
              {{ editingPromo ? "编辑促销活动" : "添加促销活动" }}
            </h3>

            <div class="space-y-4">
              <div>
                <label class="block text-xs font-medium text-neutral-500 mb-1.5">促销名称</label>
                <input
                  v-model="promoForm.name"
                  type="text"
                  placeholder="例如：618大促"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                />
              </div>

              <div>
                <label class="block text-xs font-medium text-neutral-500 mb-1.5">促销类型</label>
                <select
                  v-model="promoForm.type"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                >
                  <option value="THRESHOLD_DISCOUNT">满减</option>
                  <option value="COUPON">优惠券</option>
                  <option value="MEMBER_PRICE">会员价</option>
                </select>
              </div>

              <!-- Threshold discount fields -->
              <template v-if="promoForm.type === 'THRESHOLD_DISCOUNT'">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1.5">满减阈值（元）</label>
                    <input
                      v-model.number="promoForm.threshold_amount"
                      type="number"
                      step="0.01"
                      min="0"
                      class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1.5">减免金额（元）</label>
                    <input
                      v-model.number="promoForm.reduce_amount"
                      type="number"
                      step="0.01"
                      min="0"
                      class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                    />
                  </div>
                </div>
              </template>

              <!-- Coupon fields -->
              <template v-if="promoForm.type === 'COUPON'">
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">优惠券码</label>
                  <input
                    v-model="promoForm.coupon_code"
                    type="text"
                    placeholder="例如：SUMMER2024"
                    class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                  />
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1.5">折扣类型</label>
                    <select
                      v-model="promoForm.discount_type"
                      class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                    >
                      <option value="fixed">固定金额（元）</option>
                      <option value="percentage">百分比（%）</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1.5">折扣值</label>
                    <input
                      v-model.number="promoForm.discount_value"
                      type="number"
                      step="0.01"
                      min="0"
                      class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                    />
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">最低消费金额（元，0 表示不限）</label>
                  <input
                    v-model.number="promoForm.min_spend"
                    type="number"
                    step="0.01"
                    min="0"
                    class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                  />
                </div>
              </template>

              <!-- Member price field -->
              <template v-if="promoForm.type === 'MEMBER_PRICE'">
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">会员价格（元）</label>
                  <input
                    v-model.number="promoForm.discount_value"
                    type="number"
                    step="0.01"
                    min="0"
                    class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                  />
                </div>
              </template>

              <!-- Dates -->
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">开始日期</label>
                  <input
                    v-model="promoForm.start_date"
                    type="date"
                    class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-neutral-500 mb-1.5">结束日期</label>
                  <input
                    v-model="promoForm.end_date"
                    type="date"
                    class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 transition"
                  />
                </div>
              </div>

              <!-- Stackable -->
              <div class="flex items-center gap-3">
                <span class="text-xs font-medium text-neutral-500">是否可叠加</span>
                <button
                  type="button"
                  :class="cn(
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                    promoForm.stackable ? 'bg-primary-500' : 'bg-neutral-300'
                  )"
                  @click="promoForm.stackable = !promoForm.stackable"
                >
                  <span
                    :class="cn(
                      'inline-block size-4 rounded-full bg-white shadow transition-transform',
                      promoForm.stackable ? 'translate-x-4' : 'translate-x-0.5'
                    )"
                  />
                </button>
              </div>

              <!-- Scope -->
              <div>
                <label class="block text-xs font-medium text-neutral-500 mb-1.5">适用商品</label>
                <div class="flex gap-2">
                  <label
                    v-for="s in [{ v: 'all', l: '全部' }, { v: 'products', l: '指定商品' }, { v: 'categories', l: '指定分类' }]"
                    :key="s.v"
                    :class="cn(
                      'rounded-md px-3 py-1.5 text-xs font-medium cursor-pointer transition-colors border',
                      promoForm.scope === s.v
                        ? 'border-primary-400 bg-primary-50 text-primary-700'
                        : 'border-neutral-200 text-neutral-500 hover:border-neutral-300'
                    )"
                    @click="promoForm.scope = s.v as any"
                  >
                    {{ s.l }}
                  </label>
                </div>
              </div>
            </div>

            <div class="mt-6 flex justify-end gap-2">
              <button
                class="rounded-md border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
                @click="closePromoModal"
              >
                取消
              </button>
              <button
                class="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 active:bg-primary-800 transition-colors"
                @click="savePromotion"
              >
                {{ editingPromo ? "保存修改" : "添加促销" }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* Price preview transition */
.price-enter-active {
  transition: all 0.2s ease-out-expo;
}
.price-leave-active {
  transition: all 0.15s ease-in;
}
.price-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
.price-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}

/* Modal transition */
.modal-enter-active {
  transition: opacity 0.2s ease-out;
}
.modal-leave-active {
  transition: opacity 0.15s ease-in;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.pl-18 {
  padding-left: 4.5rem;
}

/* Custom select styling */
select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2.25rem;
}
</style>
