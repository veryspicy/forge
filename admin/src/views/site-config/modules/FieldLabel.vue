<script setup lang="ts">
import { NTooltip } from 'naive-ui';

defineProps<{
  /** 参数中文显示名（如 品牌名称 / 跳转路径）；未传时回退显示 name */
  label?: string;
  /** 参数 key（如 name / slug / hero.subtitleKey） */
  name: string;
  /** 作用说明 */
  desc?: string;
  /** 类型（string / number / boolean / string[]） */
  type?: string;
  /** 取值范围 */
  range?: string;
  /** 示例值 */
  example?: string;
}>();
</script>

<template>
  <div class="field-label flex items-center gap-1">
    <span class="text-xs font-medium text-gray-500">{{ label || name }}</span>
    <NTooltip trigger="hover" placement="top">
      <template #trigger>
        <span
          class="flex h-3.5 w-3.5 cursor-help items-center justify-center rounded-full bg-gray-200 text-[10px] leading-none text-gray-500 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300"
        >
          ?
        </span>
      </template>
      <div class="field-label-tip max-w-[260px]">
        <div v-if="desc" class="mb-1 leading-snug">{{ desc }}</div>
        <div class="mt-1 flex flex-col gap-0.5 border-t border-gray-600 border-solid pt-1 text-[11px] leading-snug">
          <div v-if="name">
            <span class="text-gray-400">字段:</span>
            <span class="font-mono break-all text-gray-100">{{ name }}</span>
          </div>
          <div v-if="type">
            <span class="text-gray-400">类型:</span>
            <span class="font-mono text-gray-100">{{ type }}</span>
          </div>
          <div v-if="range">
            <span class="text-gray-400">取值:</span>
            <span class="font-mono text-gray-100">{{ range }}</span>
          </div>
          <div v-if="example">
            <span class="text-gray-400">实例:</span>
            <span class="font-mono break-all text-gray-100">{{ example }}</span>
          </div>
        </div>
      </div>
    </NTooltip>
  </div>
</template>
