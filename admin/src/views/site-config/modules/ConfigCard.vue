<template>
  <NCard
    class="config-card"
    size="small"
    :bordered="bordered"
    :content-style="contentStyle"
    :header-style="{ padding: '8px 12px' }"
  >
    <template v-if="$slots.header || title" #header>
      <div class="flex w-full min-w-0 items-center gap-2">
        <slot name="header">
          <span class="flex-1 truncate text-[13px] font-medium text-gray-600 dark:text-gray-300">{{ title }}</span>
        </slot>
      </div>
    </template>
    <slot />
  </NCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NCard } from 'naive-ui';

const props = withDefaults(defineProps<{
  /** 卡片标题（可选，优先使用 header slot） */
  title?: string;
  /** 是否显示边框，默认 true */
  bordered?: boolean;
  /** 内容区 padding，默认 12px */
  contentPadding?: string;
}>(), {
  bordered: true,
  contentPadding: '12px'
});

const contentStyle = computed(() => ({
  padding: props.contentPadding
}));
</script>

<style scoped>
.config-card {
  /* 统一卡片样式：浅灰背景 + 明显边框 */
  --n-color: #f8fafc;
  --n-color-embedded: #f8fafc;
  --n-border-color: #d4dae3;
  --n-border-color-hover: #b9c2cf;
  --n-title-text-color: #52525b;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.04);
}
.dark .config-card {
  --n-color: rgba(255, 255, 255, 0.04);
  --n-color-embedded: rgba(255, 255, 255, 0.04);
  --n-border-color: #41414a;
  --n-border-color-hover: #565666;
}
</style>
