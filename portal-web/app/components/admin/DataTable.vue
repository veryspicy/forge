<script setup lang="ts">
interface Column {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
}

const props = defineProps<{
  columns: Column[];
  data: Record<string, any>[];
  loading?: boolean;
  selectable?: boolean;
  selected?: string[];
  currentPage?: number;
  totalPages?: number;
}>();

const emit = defineEmits<{
  "update:selected": [value: string[]];
  sort: [key: string, direction: "asc" | "desc"];
  "page-change": [page: number];
}>();

const sortKey = ref("");
const sortDir = ref<"asc" | "desc">("asc");

function handleSort(col: Column) {
  if (!col.sortable) return;
  if (sortKey.value === col.key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = col.key;
    sortDir.value = "asc";
  }
  emit("sort", sortKey.value, sortDir.value);
}

function isAllSelected(): boolean {
  return props.data.length > 0 && (props.selected?.length ?? 0) === props.data.length;
}

function toggleAll() {
  if (isAllSelected()) {
    emit("update:selected", []);
  } else {
    emit("update:selected", props.data.map((r) => r.id ?? r._key ?? String(Math.random())));
  }
}

function toggleRow(id: string) {
  const sel = props.selected ? [...props.selected] : [];
  const idx = sel.indexOf(id);
  if (idx >= 0) sel.splice(idx, 1);
  else sel.push(id);
  emit("update:selected", sel);
}
</script>

<template>
  <div class="overflow-hidden rounded border border-neutral-200 bg-white">
    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50 text-left">
            <th v-if="selectable" class="w-10 px-3 py-2.5">
              <input
                type="checkbox"
                class="size-3.5 rounded border-neutral-300 accent-accent-500"
                :checked="isAllSelected()"
                @change="toggleAll"
              />
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-4 py-2.5 font-medium text-neutral-600',
                col.sortable && 'cursor-pointer select-none hover:text-neutral-900',
                col.align === 'right' && 'text-right',
                col.align === 'center' && 'text-center',
              ]"
              :style="col.width ? { width: col.width } : {}"
              @click="handleSort(col)"
            >
              <span class="inline-flex items-center gap-1">
                {{ col.label }}
                <svg
                  v-if="col.sortable && sortKey === col.key"
                  class="size-3"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <polyline :points="sortDir === 'asc' ? '6 15 12 9 18 15' : '6 9 12 15 18 9'" />
                </svg>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Loading skeleton -->
          <tr v-if="loading">
            <td :colspan="columns.length + (selectable ? 1 : 0)" class="px-4 py-12 text-center">
              <div class="space-y-2 px-8">
                <div v-for="i in 3" :key="i" class="h-4 rounded bg-neutral-100 animate-pulse" />
              </div>
            </td>
          </tr>

          <!-- Empty state -->
          <tr v-else-if="data.length === 0">
            <td
              :colspan="columns.length + (selectable ? 1 : 0)"
              class="px-4 py-16 text-center text-neutral-400"
            >
              <p class="text-sm">暂无数据</p>
            </td>
          </tr>

          <!-- Rows -->
          <template v-else>
            <tr
              v-for="(row, ri) in data"
              :key="row.id ?? ri"
              class="border-b border-neutral-100 transition-colors hover:bg-neutral-50/60"
            >
              <td v-if="selectable" class="px-3 py-2.5">
                <input
                  type="checkbox"
                  class="size-3.5 rounded border-neutral-300 accent-accent-500"
                  :checked="selected?.includes(row.id ?? row._key) ?? false"
                  @change="toggleRow(row.id ?? row._key ?? String(ri))"
                />
              </td>
              <td
                v-for="col in columns"
                :key="col.key"
                :class="[
                  'px-4 py-2.5 text-neutral-700',
                  col.align === 'right' && 'text-right',
                  col.align === 'center' && 'text-center',
                ]"
              >
                <slot :name="col.key" :row="row" :value="row[col.key]">
                  {{ row[col.key] }}
                </slot>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      v-if="totalPages && totalPages > 1"
      class="flex items-center justify-between border-t border-neutral-200 bg-neutral-50/50 px-4 py-2.5"
    >
      <span class="text-xs text-neutral-500">
        {{ currentPage ?? 1 }} / {{ totalPages }} 页
      </span>
      <div class="flex items-center gap-1">
        <button
          :disabled="!currentPage || currentPage <= 1"
          class="rounded px-2 py-1 text-xs text-neutral-600 hover:bg-neutral-200 disabled:opacity-30 disabled:cursor-not-allowed"
          @click="emit('page-change', (currentPage ?? 1) - 1)"
        >
          上一页
        </button>
        <button
          :disabled="(currentPage ?? 1) >= totalPages"
          class="rounded px-2 py-1 text-xs text-neutral-600 hover:bg-neutral-200 disabled:opacity-30 disabled:cursor-not-allowed"
          @click="emit('page-change', (currentPage ?? 1) + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>
