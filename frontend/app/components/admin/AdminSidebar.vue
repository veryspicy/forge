<template>
  <aside
    :class="[
      'fixed inset-y-0 left-0 z-40 flex flex-col bg-neutral-900 text-neutral-100 transition-all duration-300',
      collapsed ? 'w-16' : 'w-60',
    ]"
  >
    <!-- Logo area -->
    <div class="flex h-14 items-center justify-center border-b border-neutral-700/40 shrink-0">
      <span
        v-if="!collapsed"
        class="font-heading text-sm font-semibold tracking-wide text-accent-400"
      >
        Forge Admin
      </span>
      <span v-else class="font-heading text-sm font-bold text-accent-400">PA</span>
    </div>

    <!-- Nav items -->
    <nav class="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
      <NuxtLink
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        :class="[
          'flex items-center gap-3 rounded px-3 py-2 text-sm transition-colors',
          isActive(item.to)
            ? 'bg-accent-600/20 text-accent-300'
            : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200',
        ]"
      >
        <component :is="item.icon" class="size-4 shrink-0" />
        <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- Collapse toggle -->
    <button
      class="flex h-11 items-center justify-center border-t border-neutral-700/40 text-neutral-500 hover:text-neutral-300 transition-colors shrink-0"
      @click="emit('toggle')"
    >
      <svg
        :class="['size-4 transition-transform duration-300', collapsed && 'rotate-180']"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polyline points="15 18 9 12 15 6" />
      </svg>
    </button>
  </aside>
</template>

<script setup lang="ts">
import { h, type FunctionalComponent } from "vue";
import { cn } from "~/utils/cn";

defineProps<{
  collapsed: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
}>();

const route = useRoute();

function isActive(to: string): boolean {
  if (to === "/admin") return route.path === "/admin";
  return route.path.startsWith(to);
}

// SVG icon helpers
const makeIcon = (d: string): FunctionalComponent => () =>
  h("svg", {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": "2",
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    class: "size-4 shrink-0",
    innerHTML: d,
  });

const menuItems = [
  {
    label: "仪表盘",
    to: "/admin",
    icon: makeIcon('<rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />'),
  },
  {
    label: "商品管理",
    to: "/admin/products",
    icon: makeIcon('<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />'),
  },
  {
    label: "订单管理",
    to: "/admin/orders",
    icon: makeIcon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />'),
  },
  {
    label: "供应商",
    to: "/admin/suppliers",
    icon: makeIcon('<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="8.5" cy="7" r="4" /><polyline points="17 11 19 13 23 9" />'),
  },
  {
    label: "定价引擎",
    to: "/admin/pricing",
    icon: makeIcon('<line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />'),
  },
  {
    label: "AI客服",
    to: "/admin/chat-requests",
    icon: makeIcon('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />'),
  },
  {
    label: "设置",
    to: "/admin/settings",
    icon: makeIcon('<circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />'),
  },
];
</script>
