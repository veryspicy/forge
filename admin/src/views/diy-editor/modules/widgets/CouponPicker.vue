<template>
  <div class="w-full">
    <NInput
      :value="modelValue"
      placeholder="输入优惠券 ID（优惠券管理功能即将上线）"
      @update:value="v => $emit('update:modelValue', v)"
    >
      <template #prefix>
        <SvgIcon icon="mdi:ticket-percent" />
      </template>
    </NInput>
  </div>
</template>

<script setup lang="ts">
import { NInput } from 'naive-ui';

defineProps<{
  modelValue?: string;
}>();

defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();
</script>
