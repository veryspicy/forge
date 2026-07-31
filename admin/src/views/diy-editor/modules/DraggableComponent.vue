<template>
  <div
    class="draggable-component group relative border-2 border-transparent border-solid transition-colors"
    :class="{ '!border-primary': active, 'hover:border-primary/50': !active }"
    @click.stop="$emit('click')"
  >
    <!-- 工具条 -->
    <div
      class="absolute right-0 top-0 z-10 hidden items-center gap-1 rounded-bl bg-primary/90 px-1 py-0.5 group-hover:flex"
      :class="{ '!flex': active }"
    >
      <span class="drag-handle cursor-move text-white" title="拖拽排序">
        <SvgIcon icon="mdi:drag" class="text-16px" />
      </span>
      <span class="cursor-pointer text-white" title="删除" @click.stop="$emit('remove')">
        <SvgIcon icon="mdi:delete" class="text-16px" />
      </span>
    </div>
    <div v-if="component.is_visible === false" class="opacity-40">
      <slot />
    </div>
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  component: any;
  active: boolean;
}>();

defineEmits<{
  (e: 'click'): void;
  (e: 'remove'): void;
}>();
</script>
