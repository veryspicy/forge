<script setup lang="ts">
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

const props = defineProps<{
  order: Order;
}>();

const defaultTimeline: TimelineEntry[] = [
  { label: "下单", time: props.order.created_at, active: true },
  { label: "支付", time: props.order.paid_at ?? "", active: !!props.order.paid_at },
  { label: "审核", time: "", active: false },
  { label: "采购", time: "", active: false },
  { label: "发货", time: "", active: false },
  { label: "运输", time: "", active: false },
  { label: "签收", time: "", active: false },
];

const timeline = computed(() => props.order.timeline?.length ? props.order.timeline : defaultTimeline);

function formatCurrency(val: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(val);
}

function formatDate(val: string): string {
  if (!val) return "";
  const d = new Date(val);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<template>
  <div class="grid gap-5 lg:grid-cols-3">
    <!-- Left: product list + address -->
    <div class="lg:col-span-2 space-y-4">
      <!-- Product list -->
      <div>
        <h4 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
          商品清单
        </h4>
        <div class="overflow-hidden rounded border border-neutral-200">
          <table class="min-w-full text-xs">
            <thead>
              <tr class="border-b border-neutral-200 bg-neutral-50 text-left">
                <th class="px-3 py-2 font-medium text-neutral-500">商品名称</th>
                <th class="px-3 py-2 font-medium text-neutral-500">SKU</th>
                <th class="px-3 py-2 text-center font-medium text-neutral-500">数量</th>
                <th class="px-3 py-2 text-right font-medium text-neutral-500">单价</th>
                <th class="px-3 py-2 text-right font-medium text-neutral-500">小计</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in order.items ?? []"
                :key="item.id"
                class="border-b border-neutral-100 last:border-b-0"
              >
                <td class="px-3 py-2 text-neutral-700">{{ item.name }}</td>
                <td class="px-3 py-2 font-mono text-neutral-500">{{ item.sku }}</td>
                <td class="px-3 py-2 text-center text-neutral-600">{{ item.quantity }}</td>
                <td class="px-3 py-2 text-right tabular-nums text-neutral-600">
                  {{ formatCurrency(item.unit_price) }}
                </td>
                <td class="px-3 py-2 text-right font-medium tabular-nums text-neutral-800">
                  {{ formatCurrency(item.subtotal) }}
                </td>
              </tr>
              <tr v-if="!order.items?.length">
                <td colspan="5" class="px-3 py-4 text-center text-neutral-400">
                  暂无商品明细
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Address -->
      <div v-if="order.shipping_address">
        <h4 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
          收货地址
        </h4>
        <div class="rounded border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700">
          {{ order.shipping_address }}
        </div>
      </div>
    </div>

    <!-- Right: timeline + logistics -->
    <div class="space-y-4">
      <!-- Timeline -->
      <div>
        <h4 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">
          状态时间线
        </h4>
        <div class="relative pl-5">
          <!-- Vertical line -->
          <div class="absolute left-[7px] top-1.5 bottom-1.5 w-px bg-neutral-200" />

          <div
            v-for="(entry, ei) in timeline"
            :key="ei"
            class="relative pb-4 last:pb-0"
          >
            <!-- Dot -->
            <div
              class="absolute -left-5 top-1 flex items-center justify-center"
            >
              <div
                :class="[
                  'size-2.5 rounded-full border-2',
                  entry.active
                    ? 'bg-accent-500 border-accent-500'
                    : 'bg-white border-neutral-300',
                ]"
              />
            </div>

            <div>
              <span
                :class="[
                  'text-xs font-medium',
                  entry.active ? 'text-neutral-800' : 'text-neutral-400',
                ]"
              >
                {{ entry.label }}
              </span>
              <span
                v-if="entry.time"
                class="ml-2 text-xs text-neutral-400"
              >
                {{ formatDate(entry.time) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Logistics info -->
      <div v-if="order.tracking_no || order.logistics_info">
        <h4 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
          物流信息
        </h4>
        <div class="rounded border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 space-y-1">
          <div v-if="order.tracking_no" class="flex items-center gap-2">
            <span class="text-neutral-500">运单号:</span>
            <span class="font-mono text-neutral-800">{{ order.tracking_no }}</span>
          </div>
          <div v-if="order.logistics_info">
            {{ order.logistics_info }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
