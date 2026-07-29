<template>
  <div class="property-panel h-full overflow-y-auto rounded bg-white p-4 shadow-sm dark:bg-dark">
    <div v-if="!component" class="flex h-full flex-col items-center justify-center gap-2 text-gray-400">
      <SvgIcon icon="mdi:cursor-default-click" class="text-40px" />
      <span>请选择一个组件</span>
    </div>
    <template v-else>
      <div class="mb-4 flex items-center gap-2 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
        <NButton size="tiny" quaternary type="error" @click="store.removeComponent(component.id)">
          <template #icon><SvgIcon icon="mdi:delete" /></template>
        </NButton>
        <SvgIcon :icon="component.component_icon || 'mdi:widget'" class="text-18px" />
        <span class="font-semibold">{{ component.component_name }}</span>
        <NSwitch
          :value="component.is_visible !== false"
          size="small"
          class="ml-auto"
          @update:value="toggleVisible"
        />
      </div>

      <DynamicForm
        :schema="component.config_schema"
        :model-value="component.config"
        @update:model-value="handleUpdate"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NSwitch } from 'naive-ui';
import { useDiyStore } from '@/store/modules/diy';
import DynamicForm from './DynamicForm.vue';

const store = useDiyStore();

const component = computed<any | null>(() => store.activeComponent);

function handleUpdate(config: Record<string, any>) {
  if (component.value) {
    store.updateComponentConfig(component.value.id, config);
  }
}

function toggleVisible(visible: boolean) {
  if (component.value) {
    component.value.is_visible = visible;
  }
}
</script>
