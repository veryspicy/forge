<template>
  <div class="component-panel overflow-y-auto px-2 pb-2 dark:bg-dark">
    <div v-for="group in groupedComponents" :key="group.category" class="mb-4">
      <div class="mb-2 text-xs uppercase tracking-wide text-gray-400">{{ group.label }}</div>
      <VueDraggable
        :model-value="group.items"
        :group="{ name: 'diy', pull: 'clone', put: false }"
        :sort="false"
        :clone="cloneComponent"
        item-key="id"
        class="grid grid-cols-2 gap-2"
      >
        <div
          v-for="item in group.items"
          :key="item.id"
          class="comp-item flex cursor-grab flex-col items-center gap-1 rounded border border-gray-200 border-solid p-2 text-center transition-colors hover:border-primary hover:text-primary dark:border-gray-700"
          @click="handleClickAdd(item)"
        >
          <SvgIcon :icon="item.icon || 'mdi:widget'" class="text-20px" />
          <span class="text-xs leading-tight">{{ item.name }}</span>
        </div>
      </VueDraggable>
    </div>
    <NEmpty v-if="!store.componentsLibrary.length" description="暂无组件" class="mt-10" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NEmpty } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { useDiyStore } from '@/store/modules/diy';

const store = useDiyStore();

const CATEGORY_LABELS: Record<string, string> = {
  basic: '基础组件',
  goods: '商品组件',
  marketing: '营销组件',
  layout: '布局组件'
};

const groupedComponents = computed(() => {
  const groups: { category: string; label: string; items: any[] }[] = [];
  for (const item of store.componentsLibrary) {
    let g = groups.find(x => x.category === item.category);
    if (!g) {
      g = { category: item.category, label: CATEGORY_LABELS[item.category] || item.category, items: [] };
      groups.push(g);
    }
    g.items.push(item);
  }
  return groups;
});

/** 拖拽克隆：把组件库定义转换为画布中的 PageComponent 实例 */
function cloneComponent(component: any) {
  return {
    id: crypto.randomUUID(),
    page_id: store.currentPage?.id,
    component_id: component.id,
    component_code: component.code,
    component_name: component.name,
    component_icon: component.icon,
    config_schema: component.config_schema || {},
    sort_order: 0,
    config: JSON.parse(JSON.stringify(component.default_config || {})),
    is_visible: true
  };
}

function handleClickAdd(component: any) {
  store.addComponent(component);
  window.$message?.success(`已添加「${component.name}」`);
}
</script>

<style scoped>
.comp-item:active {
  cursor: grabbing;
}
</style>
