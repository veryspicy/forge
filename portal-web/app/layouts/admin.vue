<template>
  <div class="flex min-h-screen bg-neutral-50">
    <!-- Sidebar -->
    <AdminSidebar :collapsed="sidebarCollapsed" @toggle="toggleSidebar" />

    <!-- Mobile overlay -->
    <div
      v-if="sidebarCollapsed === false && isMobile"
      class="fixed inset-0 z-30 bg-black/30 lg:hidden"
      @click="toggleSidebar"
    />

    <!-- Main content -->
    <div
      :class="[
        'flex flex-1 flex-col transition-all duration-300',
        sidebarCollapsed ? 'ml-16' : 'ml-60',
      ]"
    >
      <!-- Top bar -->
      <header class="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-neutral-200 bg-white px-6">
        <!-- Breadcrumb -->
        <nav class="flex items-center gap-1.5 text-sm">
          <template v-for="(crumb, i) in breadcrumbs" :key="i">
            <span v-if="i > 0" class="text-neutral-300">/</span>
            <span :class="i === breadcrumbs.length - 1 ? 'font-medium text-neutral-800' : 'text-neutral-500'">
              {{ crumb }}
            </span>
          </template>
        </nav>

        <!-- User menu -->
        <div class="relative">
          <button
            class="flex items-center gap-2 rounded px-2 py-1 text-sm text-neutral-600 hover:bg-neutral-100"
            @click="showUserMenu = !showUserMenu"
          >
            <span class="size-7 rounded-full bg-accent-100 text-accent-700 flex items-center justify-center text-xs font-bold">
              {{ userInitial }}
            </span>
            <span class="hidden sm:inline">{{ userEmail }}</span>
            <svg class="size-3.5 text-neutral-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          <!-- Dropdown -->
          <div
            v-if="showUserMenu"
            class="absolute right-0 top-full mt-1 w-44 rounded border border-neutral-200 bg-white py-1 shadow-lg"
          >
            <button
              class="w-full px-4 py-2 text-left text-sm text-neutral-700 hover:bg-neutral-50"
              @click="handleLogout"
            >
              退出登录
            </button>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";

const route = useRoute();
const authStore = useAuthStore();
const { isAuthenticated, user } = storeToRefs(authStore);
const { logout } = authStore;
const adminStore = useAdminStore();
const { sidebarCollapsed } = storeToRefs(adminStore);
const { toggleSidebar } = adminStore;

const isMobile = ref(false);
const showUserMenu = ref(false);

const breadcrumbs = computed(() => {
  const map: Record<string, string> = {
    admin: "仪表盘",
    products: "商品管理",
    orders: "订单管理",
    suppliers: "供应商",
    pricing: "定价引擎",
    "chat-requests": "AI客服",
    settings: "设置",
  };
  const parts = route.path.split("/").filter(Boolean);
  return parts.map((p) => map[p] ?? p);
});

const userEmail = computed(() => (user.value?.email as string) ?? "Admin");
const userInitial = computed(() => (userEmail.value?.[0] ?? "A").toUpperCase());

function handleResize() {
  isMobile.value = window.innerWidth < 1024;
  if (isMobile.value && !sidebarCollapsed.value) {
    toggleSidebar();
  }
}

function handleClickOutside(e: MouseEvent) {
  if (showUserMenu.value) {
    showUserMenu.value = false;
  }
}

function handleLogout() {
  logout();
  showUserMenu.value = false;
  navigateTo("/login");
}

onMounted(() => {
  handleResize();
  window.addEventListener("resize", handleResize);
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  document.removeEventListener("click", handleClickOutside);
});
</script>
