<script setup lang="ts">
defineProps<{
  title: string;
  value: string | number;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
}>();

const trendArrow = {
  up: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
  down: "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6",
  neutral: "M5 12h14",
};

const trendColor = {
  up: "text-success",
  down: "text-error",
  neutral: "text-neutral-400",
};
</script>

<template>
  <div class="rounded bg-primary-50 border border-primary-100 px-5 py-4">
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0">
        <p class="text-xs font-medium tracking-wide text-neutral-500 uppercase">
          {{ title }}
        </p>
        <p class="mt-1 text-2xl font-heading font-bold text-neutral-900 tabular-nums">
          {{ value }}
        </p>
      </div>
      <div v-if="trend && trendValue" class="flex items-center gap-1 text-xs shrink-0" :class="trendColor[trend]">
        <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline :points="trendArrow[trend]" />
        </svg>
        <span class="font-medium tabular-nums">{{ trendValue }}</span>
      </div>
    </div>
  </div>
</template>
