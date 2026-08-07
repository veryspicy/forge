<script setup lang="ts">
interface Props {
  status: string;
}

const props = defineProps<Props>();

const statusMap: Record<string, { label: string; color: string }> = {
  waiting: { label: "等待中", color: "oklch(0.50 0.00 145)" },
  ai_processing: { label: "AI处理中", color: "oklch(0.50 0.12 250)" },
  pending_takeover: { label: "待人工接管", color: "oklch(0.55 0.16 85)" },
  human_processing: { label: "人工处理中", color: "oklch(0.45 0.10 280)" },
  resolved: { label: "已解决", color: "oklch(0.55 0.15 160)" },
};

const normalized = props.status?.toLowerCase().replace(/[\s-]+/g, "_") ?? "";
const info = statusMap[normalized] ?? { label: props.status, color: "oklch(0.55 0.00 145)" };
</script>

<template>
  <span class="inline-flex items-center gap-1.5 text-[11px] font-medium whitespace-nowrap">
    <span
      class="inline-block size-1.5 rounded-full shrink-0"
      :style="{ backgroundColor: info.color }"
    />
    {{ info.label }}
  </span>
</template>
