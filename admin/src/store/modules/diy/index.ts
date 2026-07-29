import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { diyApi } from '@/service/api/diy';

/** DIY 页面装修编辑器状态 */
export const useDiyStore = defineStore('diy-store', () => {
  /** 当前编辑的页面数据（含 components 数组） */
  const currentPage = ref<any | null>(null);
  /** 组件库列表 */
  const componentsLibrary = ref<any[]>([]);
  /** 当前选中的画布组件 id */
  const activeComponentId = ref<string | null>(null);

  const pageComponents = computed<any[]>({
    get: () => currentPage.value?.components ?? [],
    set: (val: any[]) => {
      if (currentPage.value) {
        currentPage.value.components = val;
      }
    }
  });

  const activeComponent = computed<any | null>(
    () => pageComponents.value.find(c => c.id === activeComponentId.value) ?? null
  );

  async function fetchPage(id: string) {
    const res = await diyApi.getPage(id);
    currentPage.value = res.data;
    activeComponentId.value = null;
  }

  async function fetchComponentsLibrary() {
    const res = await diyApi.getComponents();
    componentsLibrary.value = res.data || [];
  }

  /** 从组件库添加组件到画布（使用 default_config 作为初始配置） */
  function addComponent(component: any, index?: number) {
    if (!currentPage.value) return;
    const pc = {
      id: crypto.randomUUID(),
      page_id: currentPage.value.id,
      component_id: component.id,
      component_code: component.code,
      component_name: component.name,
      component_icon: component.icon,
      config_schema: component.config_schema || {},
      sort_order: 0,
      config: JSON.parse(JSON.stringify(component.default_config || {})),
      is_visible: true
    };
    const list = [...pageComponents.value];
    const insertAt = index === undefined || index < 0 ? list.length : index;
    list.splice(insertAt, 0, pc);
    list.forEach((c, i) => {
      c.sort_order = i;
    });
    pageComponents.value = list;
    activeComponentId.value = pc.id;
  }

  function removeComponent(id: string) {
    pageComponents.value = pageComponents.value
      .filter(c => c.id !== id)
      .map((c, i) => ({ ...c, sort_order: i }));
    if (activeComponentId.value === id) {
      activeComponentId.value = null;
    }
  }

  function selectComponent(id: string | null) {
    activeComponentId.value = id;
  }

  function updateComponentConfig(id: string, config: Record<string, any>) {
    const target = pageComponents.value.find(c => c.id === id);
    if (target) {
      target.config = { ...target.config, ...config };
    }
  }

  /** 画布拖拽结束后同步 sort_order */
  function reorderComponents(newOrder: any[]) {
    newOrder.forEach((c, i) => {
      c.sort_order = i;
    });
    pageComponents.value = newOrder;
  }

  /** 整页保存组件列表 */
  async function saveComponents(pageId: string) {
    const payload = pageComponents.value.map((c, i) => ({
      component_id: c.component_id,
      sort_order: i,
      config: c.config || {},
      is_visible: c.is_visible !== false
    }));
    return diyApi.saveComponents(pageId, payload);
  }

  function reset() {
    currentPage.value = null;
    activeComponentId.value = null;
  }

  return {
    currentPage,
    componentsLibrary,
    activeComponentId,
    pageComponents,
    activeComponent,
    fetchPage,
    fetchComponentsLibrary,
    addComponent,
    removeComponent,
    selectComponent,
    updateComponentConfig,
    reorderComponents,
    saveComponents,
    reset
  };
});
