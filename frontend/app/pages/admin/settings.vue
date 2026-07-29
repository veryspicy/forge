<script setup lang="ts">
import { getSettings, updateSettings } from "~/composables/useAdminApi";

definePageMeta({
  layout: "admin",
  middleware: "auth",
});

// ==================== State ====================

const loading = ref(true);
const saveLoading: Record<string, boolean> = reactive({
  apiKeys: false,
  permissions: false,
  system: false,
  notifications: false,
});

// ---- Section 1: MCP API Keys ----
interface ApiKeyItem {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  status: "active" | "revoked";
  key_prefix: string;
}
const apiKeys = ref<ApiKeyItem[]>([]);
const showGenerateModal = ref(false);
const newKeyName = ref("");
const generatedKey = ref("");
const generating = ref(false);

// ---- Section 2: Role Permissions ----
interface UserItem {
  id: string;
  username: string;
  email: string;
  role: "admin" | "operator" | "support";
}
const users = ref<UserItem[]>([]);
const showAddUserModal = ref(false);
const newUser = reactive({ username: "", email: "", password: "", role: "support" as string });

// ---- Section 3: System Parameters ----
const systemParams = reactive({
  aiProbeThreshold: 50,
  autoCreateProduct: false,
  defaultPricingMultiplier: 2.0,
  defaultShippingFee: 5,
});

// ---- Section 4: Notification Settings ----
const notificationSettings = reactive({
  newOrderNotification: true,
  procurementAlert: true,
  lowStockThreshold: 10,
});

// ==================== Load Data ====================

async function loadSettings() {
  loading.value = true;
  try {
    const data: any = await getSettings();

    // Parse API keys
    apiKeys.value = (data?.api_keys ?? []).map((k: any) => ({
      id: k.id ?? "",
      name: k.name ?? "",
      created_at: k.created_at ?? "",
      last_used_at: k.last_used_at ?? null,
      status: k.status ?? "active",
      key_prefix: k.key_prefix ?? "mcp-",
    }));

    // Parse users
    users.value = (data?.users ?? []).map((u: any) => ({
      id: u.id ?? "",
      username: u.username ?? "",
      email: u.email ?? "",
      role: u.role ?? "support",
    }));

    // Parse system params
    if (data?.system) {
      systemParams.aiProbeThreshold = data.system.ai_probe_threshold ?? data.system.aiProbeThreshold ?? 50;
      systemParams.autoCreateProduct = data.system.auto_create_product ?? data.system.autoCreateProduct ?? false;
      systemParams.defaultPricingMultiplier = data.system.default_pricing_multiplier ?? data.system.defaultPricingMultiplier ?? 2.0;
      systemParams.defaultShippingFee = data.system.default_shipping_fee ?? data.system.defaultShippingFee ?? 5;
    }

    // Parse notification settings
    if (data?.notifications) {
      notificationSettings.newOrderNotification = data.notifications.new_order ?? data.notifications.newOrderNotification ?? true;
      notificationSettings.procurementAlert = data.notifications.procurement_alert ?? data.notifications.procurementAlert ?? true;
      notificationSettings.lowStockThreshold = data.notifications.low_stock_threshold ?? data.notifications.lowStockThreshold ?? 10;
    }
  } catch {
    // Keep defaults on error
  } finally {
    loading.value = false;
  }
}

// ==================== Section 1: API Keys ====================

async function generateApiKey() {
  generating.value = true;
  try {
    const res: any = await updateSettings({
      action: "generate_key",
      name: newKeyName.value || `Key ${apiKeys.value.length + 1}`,
    });
    generatedKey.value = res?.key ?? res?.api_key ?? "";
    // Reload to get updated list
    await loadSettings();
    showGenerateModal.value = false;
  } catch {
    // Error handled by interceptor
  } finally {
    generating.value = false;
  }
}

async function revokeApiKey(id: string) {
  saveLoading.apiKeys = true;
  try {
    await updateSettings({ action: "revoke_key", key_id: id });
    await loadSettings();
  } catch {
    // Error handled by interceptor
  } finally {
    saveLoading.apiKeys = false;
  }
}

async function regenerateApiKey(id: string) {
  generating.value = true;
  try {
    const res: any = await updateSettings({ action: "regenerate_key", key_id: id });
    generatedKey.value = res?.key ?? res?.api_key ?? "";
    showGenerateModal.value = true;
    await loadSettings();
  } catch {
    // Error handled by interceptor
  } finally {
    generating.value = false;
  }
}

function openGenerateModal() {
  newKeyName.value = "";
  generatedKey.value = "";
  showGenerateModal.value = true;
}

function copyKeyToClipboard() {
  navigator.clipboard.writeText(generatedKey.value);
}

// ==================== Section 2: Permissions ====================

async function changeUserRole(id: string, role: string) {
  saveLoading.permissions = true;
  try {
    await updateSettings({ action: "update_user_role", user_id: id, role });
    await loadSettings();
  } catch {
    // Reload to revert
    await loadSettings();
  } finally {
    saveLoading.permissions = false;
  }
}

function openAddUserModal() {
  newUser.username = "";
  newUser.email = "";
  newUser.password = "";
  newUser.role = "support";
  showAddUserModal.value = true;
}

async function addUser() {
  saveLoading.permissions = true;
  try {
    await updateSettings({
      action: "add_user",
      username: newUser.username,
      email: newUser.email,
      password: newUser.password,
      role: newUser.role,
    });
    showAddUserModal.value = false;
    await loadSettings();
  } catch {
    // Error handled by interceptor
  } finally {
    saveLoading.permissions = false;
  }
}

// ==================== Section 3: System ====================

async function saveSystemParams() {
  saveLoading.system = true;
  try {
    await updateSettings({
      action: "update_system",
      ai_probe_threshold: systemParams.aiProbeThreshold,
      auto_create_product: systemParams.autoCreateProduct,
      default_pricing_multiplier: systemParams.defaultPricingMultiplier,
      default_shipping_fee: systemParams.defaultShippingFee,
    });
    await loadSettings();
  } catch {
    // Error handled by interceptor
  } finally {
    saveLoading.system = false;
  }
}

// ==================== Section 4: Notifications ====================

async function saveNotificationSettings() {
  saveLoading.notifications = true;
  try {
    await updateSettings({
      action: "update_notifications",
      new_order: notificationSettings.newOrderNotification,
      procurement_alert: notificationSettings.procurementAlert,
      low_stock_threshold: notificationSettings.lowStockThreshold,
    });
    await loadSettings();
  } catch {
    // Error handled by interceptor
  } finally {
    saveLoading.notifications = false;
  }
}

// ==================== Helpers ====================

const roleOptions = [
  { value: "admin", label: "管理员" },
  { value: "operator", label: "运营" },
  { value: "support", label: "客服" },
];

function roleLabel(role: string): string {
  return roleOptions.find((r) => r.value === role)?.label ?? role;
}

function formatDate(raw: string): string {
  if (!raw) return "-";
  const d = new Date(raw);
  if (isNaN(d.getTime())) return raw;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// Shorthand for common styles
function btn(
  variant: "primary" | "secondary" | "danger" | "ghost",
  loading?: boolean,
) {
  const base = "inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const variants: Record<string, string> = {
    primary: "bg-accent-500 text-white hover:bg-accent-600",
    secondary: "border border-neutral-300 text-neutral-700 hover:bg-neutral-100",
    danger: "bg-red-50 text-red-700 border border-red-200 hover:bg-red-100",
    ghost: "text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100",
  };
  return [base, variants[variant], loading ? "animate-pulse" : ""].join(" ");
}

onMounted(() => {
  loadSettings();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-heading font-bold tracking-tight text-neutral-900">
        系统设置
      </h1>
      <p class="mt-0.5 text-sm text-neutral-500">管理 API Key、权限、参数与通知</p>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 4" :key="i" class="rounded border border-neutral-200 bg-white px-6 py-8">
        <div class="mb-5 h-5 w-36 animate-pulse rounded bg-neutral-200" />
        <div class="space-y-3">
          <div class="h-4 w-full animate-pulse rounded bg-neutral-100" />
          <div class="h-4 w-3/4 animate-pulse rounded bg-neutral-100" />
        </div>
      </div>
    </div>

    <template v-else>
    <!-- ========== Section 1: MCP API Keys ========== -->
    <section class="rounded border border-neutral-200 bg-white">
      <div class="flex items-center justify-between px-6 py-4">
        <h2 class="text-sm font-semibold tracking-wide text-neutral-700 uppercase">
          MCP API Key 管理
        </h2>
        <button
          :class="btn('primary')"
          @click="openGenerateModal"
        >
          <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          生成新 Key
        </button>
      </div>

      <div class="border-t border-neutral-100" />

      <!-- Keys table -->
      <div class="overflow-x-auto px-6 pb-4">
        <table v-if="apiKeys.length > 0" class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 text-left">
              <th class="py-2.5 pr-4 font-medium text-neutral-500">名称</th>
              <th class="py-2.5 pr-4 font-medium text-neutral-500">创建时间</th>
              <th class="py-2.5 pr-4 font-medium text-neutral-500">最后使用</th>
              <th class="py-2.5 pr-4 font-medium text-neutral-500">状态</th>
              <th class="py-2.5 font-medium text-neutral-500">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="key in apiKeys"
              :key="key.id"
              class="border-b border-neutral-100/60 last:border-0"
            >
              <td class="py-2.5 pr-4">
                <span class="font-medium text-neutral-800">{{ key.name }}</span>
                <div class="mt-0.5 font-mono text-[11px] text-neutral-400">
                  {{ key.key_prefix || "mcp-" }}...
                </div>
              </td>
              <td class="py-2.5 pr-4 tabular-nums text-neutral-600">
                {{ formatDate(key.created_at) }}
              </td>
              <td class="py-2.5 pr-4 tabular-nums text-neutral-500">
                {{ key.last_used_at ? formatDate(key.last_used_at) : "从未使用" }}
              </td>
              <td class="py-2.5 pr-4">
                <span class="inline-flex items-center gap-1.5 text-xs">
                  <span
                    class="inline-block size-2 rounded-full shrink-0"
                    :class="key.status === 'active' ? 'bg-green-500' : 'bg-red-400'"
                  />
                  <span :class="key.status === 'active' ? 'text-green-700' : 'text-red-600'">
                    {{ key.status === "active" ? "活跃" : "已吊销" }}
                  </span>
                </span>
              </td>
              <td class="py-2.5">
                <div class="flex items-center gap-2">
                  <button
                    :class="btn('ghost')"
                    :disabled="saveLoading.apiKeys"
                    @click="regenerateApiKey(key.id)"
                  >
                    重新生成
                  </button>
                  <button
                    v-if="key.status === 'active'"
                    :class="btn('danger')"
                    :disabled="saveLoading.apiKeys"
                    @click="revokeApiKey(key.id)"
                  >
                    吊销
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-else class="py-12 text-center text-sm text-neutral-400">
          暂无 API Key，点击上方按钮生成
        </div>
      </div>
    </section>

    <!-- ========== Section 2: Role Permissions ========== -->
    <section class="rounded border border-neutral-200 bg-white">
      <div class="flex items-center justify-between px-6 py-4">
        <h2 class="text-sm font-semibold tracking-wide text-neutral-700 uppercase">
          角色权限配置
        </h2>
        <button
          :class="btn('primary')"
          @click="openAddUserModal"
        >
          <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          添加用户
        </button>
      </div>

      <div class="border-t border-neutral-100" />

      <div class="overflow-x-auto px-6 pb-4">
        <table v-if="users.length > 0" class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 text-left">
              <th class="py-2.5 pr-4 font-medium text-neutral-500">用户名</th>
              <th class="py-2.5 pr-4 font-medium text-neutral-500">邮箱</th>
              <th class="py-2.5 pr-4 font-medium text-neutral-500">角色</th>
              <th class="py-2.5 font-medium text-neutral-500">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in users"
              :key="user.id"
              class="border-b border-neutral-100/60 last:border-0"
            >
              <td class="py-2.5 pr-4 font-medium text-neutral-800">
                {{ user.username }}
              </td>
              <td class="py-2.5 pr-4 tabular-nums text-neutral-500">
                {{ user.email || "-" }}
              </td>
              <td class="py-2.5 pr-4">
                <select
                  :value="user.role"
                  :disabled="saveLoading.permissions"
                  class="rounded border border-neutral-300 bg-white px-2.5 py-1 text-xs text-neutral-700 focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400 disabled:opacity-50"
                  @change="changeUserRole(user.id, ($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </td>
              <td class="py-2.5">
                <span class="text-xs text-neutral-400">{{ roleLabel(user.role) }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-else class="py-12 text-center text-sm text-neutral-400">
          暂无用户
        </div>
      </div>
    </section>

    <!-- ========== Section 3: System Parameters ========== -->
    <section class="rounded border border-neutral-200 bg-white">
      <div class="flex items-center justify-between px-6 py-4">
        <h2 class="text-sm font-semibold tracking-wide text-neutral-700 uppercase">
          系统参数
        </h2>
        <button
          :class="btn('primary', saveLoading.system)"
          :disabled="saveLoading.system"
          @click="saveSystemParams"
        >
          <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          保存
        </button>
      </div>

      <div class="border-t border-neutral-100" />

      <div class="divide-y divide-neutral-100 px-6 py-2">
        <!-- AI Probe threshold -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">AI 探针阈值</label>
            <p class="mt-0.5 text-xs text-neutral-400">触发自动比价的最低价格阈值</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-neutral-500">CNY</span>
            <input
              v-model.number="systemParams.aiProbeThreshold"
              type="number"
              min="0"
              class="w-28 rounded border border-neutral-300 px-3 py-1.5 text-right text-sm tabular-nums focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
            />
          </div>
        </div>

        <!-- Auto-create product toggle -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">自动创建商品</label>
            <p class="mt-0.5 text-xs text-neutral-400">探针发现新品时自动录入商品库</p>
          </div>
          <!-- Pure CSS toggle -->
          <label class="relative inline-flex cursor-pointer items-center">
            <input
              v-model="systemParams.autoCreateProduct"
              type="checkbox"
              class="peer sr-only"
            />
            <div
              class="h-5 w-9 rounded-full bg-neutral-300 transition-colors peer-checked:bg-accent-500 peer-focus-visible:ring-2 peer-focus-visible:ring-accent-400 peer-focus-visible:ring-offset-1"
            />
            <div
              class="absolute left-0.5 top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4"
            />
          </label>
        </div>

        <!-- Default pricing multiplier -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">默认定价倍率</label>
            <p class="mt-0.5 text-xs text-neutral-400">定价引擎默认的成本倍率系数</p>
          </div>
          <div class="flex items-center gap-1">
            <input
              v-model.number="systemParams.defaultPricingMultiplier"
              type="number"
              min="0.1"
              step="0.1"
              class="w-24 rounded border border-neutral-300 px-3 py-1.5 text-right text-sm tabular-nums focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
            />
            <span class="text-xs text-neutral-500">x</span>
          </div>
        </div>

        <!-- Default shipping fee -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">默认固定运费</label>
            <p class="mt-0.5 text-xs text-neutral-400">未配置运费时的默认值</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-neutral-500">CNY</span>
            <input
              v-model.number="systemParams.defaultShippingFee"
              type="number"
              min="0"
              class="w-28 rounded border border-neutral-300 px-3 py-1.5 text-right text-sm tabular-nums focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ========== Section 4: Notification Settings ========== -->
    <section class="rounded border border-neutral-200 bg-white">
      <div class="flex items-center justify-between px-6 py-4">
        <h2 class="text-sm font-semibold tracking-wide text-neutral-700 uppercase">
          通知设置
        </h2>
        <button
          :class="btn('primary', saveLoading.notifications)"
          :disabled="saveLoading.notifications"
          @click="saveNotificationSettings"
        >
          <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          保存
        </button>
      </div>

      <div class="border-t border-neutral-100" />

      <div class="divide-y divide-neutral-100 px-6 py-2">
        <!-- New order notification -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">新订单通知</label>
            <p class="mt-0.5 text-xs text-neutral-400">有新订单时推送通知</p>
          </div>
          <label class="relative inline-flex cursor-pointer items-center">
            <input
              v-model="notificationSettings.newOrderNotification"
              type="checkbox"
              class="peer sr-only"
            />
            <div
              class="h-5 w-9 rounded-full bg-neutral-300 transition-colors peer-checked:bg-accent-500 peer-focus-visible:ring-2 peer-focus-visible:ring-accent-400 peer-focus-visible:ring-offset-1"
            />
            <div
              class="absolute left-0.5 top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4"
            />
          </label>
        </div>

        <!-- Procurement alert -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">采购异常通知</label>
            <p class="mt-0.5 text-xs text-neutral-400">采购流程出现异常时推送通知</p>
          </div>
          <label class="relative inline-flex cursor-pointer items-center">
            <input
              v-model="notificationSettings.procurementAlert"
              type="checkbox"
              class="peer sr-only"
            />
            <div
              class="h-5 w-9 rounded-full bg-neutral-300 transition-colors peer-checked:bg-accent-500 peer-focus-visible:ring-2 peer-focus-visible:ring-accent-400 peer-focus-visible:ring-offset-1"
            />
            <div
              class="absolute left-0.5 top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4"
            />
          </label>
        </div>

        <!-- Low stock threshold -->
        <div class="flex items-center justify-between py-3">
          <div>
            <label class="text-sm font-medium text-neutral-800">低库存预警阈值</label>
            <p class="mt-0.5 text-xs text-neutral-400">库存低于此数量时发送预警通知</p>
          </div>
          <div class="flex items-center gap-1">
            <input
              v-model.number="notificationSettings.lowStockThreshold"
              type="number"
              min="0"
              class="w-24 rounded border border-neutral-300 px-3 py-1.5 text-right text-sm tabular-nums focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
            />
            <span class="text-xs text-neutral-500">件</span>
          </div>
        </div>
      </div>
    </section>
    </template>
  </div>

  <!-- ========== Generate Key Modal ========== -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="showGenerateModal"
        class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto pt-[15vh]"
        @click.self="showGenerateModal = false"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-neutral-900/40" />

        <!-- Modal -->
        <div
          class="relative w-full max-w-md rounded-lg bg-white shadow-lg animate-scale-in"
          role="dialog"
          aria-modal="true"
        >
          <!-- Header -->
          <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-3.5">
            <h3 class="text-sm font-semibold text-neutral-900">
              {{ generatedKey ? "API Key 已生成" : "生成新 API Key" }}
            </h3>
            <button
              class="rounded p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
              @click="showGenerateModal = false"
            >
              <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div class="px-5 py-4">
            <!-- Before generation: name input -->
            <div v-if="!generatedKey">
              <label class="block text-xs font-medium text-neutral-600 mb-1.5">
                Key 名称
              </label>
              <input
                v-model="newKeyName"
                type="text"
                placeholder="例如：生产环境、测试环境"
                class="w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
                @keyup.enter="generateApiKey"
              />
              <p class="mt-1.5 text-[11px] text-neutral-400">
                生成后 Key 值仅显示一次，系统仅存储 SHA-256 哈希，请妥善保存。
              </p>
            </div>

            <!-- After generation: show the key -->
            <div v-else>
              <div class="rounded border border-amber-200 bg-amber-50 px-4 py-3">
                <p class="text-xs font-medium text-amber-800 mb-2">
                  请立即复制并保存此 Key，关闭后无法再次查看
                </p>
                <div class="flex items-center gap-2">
                  <code class="flex-1 break-all rounded bg-white px-3 py-2 text-xs font-mono border border-amber-200 text-neutral-800 select-all">
                    {{ generatedKey }}
                  </code>
                  <button
                    class="shrink-0 rounded p-2 text-neutral-500 hover:bg-white hover:text-accent-600 transition-colors border border-neutral-200"
                    title="复制到剪贴板"
                    @click="copyKeyToClipboard"
                  >
                    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  </button>
                </div>
              </div>
              <p class="mt-2 text-[11px] text-neutral-400">
                该 Key 的 SHA-256 哈希已存储，原始值不可恢复。
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex justify-end gap-2 border-t border-neutral-100 px-5 py-3">
            <button
              v-if="!generatedKey"
              :class="btn('secondary')"
              @click="showGenerateModal = false"
            >
              取消
            </button>
            <template v-else>
              <button
                :class="btn('secondary')"
                @click="copyKeyToClipboard"
              >
                复制并关闭
              </button>
            </template>
            <button
              v-if="!generatedKey"
              :class="btn('primary', generating)"
              :disabled="generating"
              @click="generateApiKey"
            >
              {{ generating ? "生成中..." : "确认生成" }}
            </button>
            <button
              v-else
              :class="btn('primary')"
              @click="showGenerateModal = false"
            >
              我已保存，关闭
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ========== Add User Modal ========== -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="showAddUserModal"
        class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto pt-[15vh]"
        @click.self="showAddUserModal = false"
      >
        <div class="fixed inset-0 bg-neutral-900/40" />

        <div
          class="relative w-full max-w-sm rounded-lg bg-white shadow-lg animate-scale-in"
          role="dialog"
          aria-modal="true"
        >
          <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-3.5">
            <h3 class="text-sm font-semibold text-neutral-900">添加用户</h3>
            <button
              class="rounded p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
              @click="showAddUserModal = false"
            >
              <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div class="space-y-3.5 px-5 py-4">
            <div>
              <label class="block text-xs font-medium text-neutral-600 mb-1">用户名</label>
              <input
                v-model="newUser.username"
                type="text"
                class="w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-600 mb-1">邮箱</label>
              <input
                v-model="newUser.email"
                type="email"
                class="w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-600 mb-1">密码</label>
              <input
                v-model="newUser.password"
                type="password"
                class="w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-600 mb-1">角色</label>
              <select
                v-model="newUser.role"
                class="w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 focus:border-accent-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
              >
                <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-2 border-t border-neutral-100 px-5 py-3">
            <button
              :class="btn('secondary')"
              @click="showAddUserModal = false"
            >
              取消
            </button>
            <button
              :class="btn('primary', saveLoading.permissions)"
              :disabled="saveLoading.permissions || !newUser.username || !newUser.password"
              @click="addUser"
            >
              {{ saveLoading.permissions ? "添加中..." : "确认添加" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
