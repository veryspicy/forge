<script setup lang="ts">
interface Props {
  status: string;
}

const props = defineProps<Props>();

const statusMap: Record<string, { label: string; color: string }> = {
  pending_payment: { label: "待支付", color: "oklch(0.65 0.16 85)" },
  paid: { label: "已支付", color: "oklch(0.50 0.12 250)" },
  procuring: { label: "采购中", color: "oklch(0.45 0.10 280)" },
  shipped: { label: "已发货", color: "oklch(0.50 0.12 180)" },
  in_transit: { label: "运输中", color: "oklch(0.55 0.12 200)" },
  delivered: { label: "已送达", color: "oklch(0.55 0.15 160)" },
  completed: { label: "已完成", color: "oklch(0.45 0.01 145)" },
  procurement_failed: { label: "采购异常", color: "oklch(0.52 0.18 25)" },
};

const normalized = props.status.toLowerCase().replace(/[\s-]+/g, "_");
const info = statusMap[normalized] ?? { label: props.status, color: "oklch(0.55 0.00 145)" };
</script>

<template>
  <span class="inline-flex items-center gap-1.5 text-xs font-medium whitespace-nowrap">
    <span
      class="inline-block size-2 rounded-full shrink-0"
      :style="{ backgroundColor: info.color }"
    />
    {{ info.label }}
  </span>
</template>
