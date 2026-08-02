import { computed, reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import { diyApi } from '@/service/api/diy';
import { get as httpGet, put as httpPut } from '@/service/api/helper';

/** 站点配置项的 key 列表 */
export const SITE_CONFIG_ITEMS = [
  { key: 'brand', label: '品牌', icon: 'mdi:tag-text' },
  { key: 'theme', label: '主题', icon: 'mdi:palette' },
  { key: 'nav', label: '导航', icon: 'mdi:menu' },
  { key: 'categories', label: '分类', icon: 'mdi:shape' },
  { key: 'footer', label: '页脚', icon: 'mdi:page-layout-footer' },
  { key: 'seo', label: 'SEO', icon: 'mdi:magnify' },
  { key: 'i18n', label: 'i18n', icon: 'mdi:translate' },
  { key: 'featureFlags', label: '功能开关', icon: 'mdi:toggle-switch' },
  { key: 'currencies', label: '货币', icon: 'mdi:cash' }
] as const;

export type SiteConfigKey = (typeof SITE_CONFIG_ITEMS)[number]['key'];

const DEFAULT_SITE_CONFIG = {
  brand: { name: 'Forge', tagline: '', logo: { type: 'text', data: '' } },
  theme: {
    primaryColor: '#18a058', primaryLight: '#36ad6a', primaryDark: '#0c7a43',
    secondaryColor: '#f0a020', accentColor: '#2080f0', fontHeading: 'Inter', fontBody: 'Inter'
  },
  nav: [] as { label: string; url: string }[],
  categories: [] as { slug: string; nameKey: string; icon: string }[],
  footer: { copyright: '', newsletter: true },
  seo: { homeTitle: '', metaDescription: '', metaKeywords: '' },
  i18n: { defaultLocale: 'en', locales: ['en'] as string[] },
  featureFlags: {} as Record<string, boolean>,
  currencies: ['USD'] as string[],
  regions: [] as string[]
};

/** DIY 页面装修编辑器状态 */
export const useDiyStore = defineStore('diy-store', () => {
  /** 当前编辑的页面数据（含 components 数组） */
  const currentPage = ref<any | null>(null);
  /** 组件库列表 */
  const componentsLibrary = ref<any[]>([]);
  /** 当前选中的画布组件 id */
  const activeComponentId = ref<string | null>(null);
  /** 当前选中的站点配置项 key */
  const activeSiteConfigItem = ref<SiteConfigKey | null>(null);
  /** 站点配置数据 */
  const siteConfig = reactive<any>(JSON.parse(JSON.stringify(DEFAULT_SITE_CONFIG)));

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

  /** 选择站点配置项 */
  function selectSiteConfigItem(key: SiteConfigKey | null) {
    activeSiteConfigItem.value = key;
    // 选择站点配置时取消组件选中
    if (key) activeComponentId.value = null;
  }

  /** 加载站点配置 */
  async function fetchSiteConfig() {
    try {
      const res = await httpGet('/api/admin/v1/site/config');
      if (res.data) {
        Object.keys(DEFAULT_SITE_CONFIG).forEach(k => {
          if (res.data[k] !== undefined) {
            siteConfig[k] = JSON.parse(JSON.stringify(res.data[k]));
          }
        });
      }
    } catch { /* 配置未就绪时使用默认值 */ }
  }

  /** 保存站点配置 */
  async function saveSiteConfig() {
    return httpPut('/api/admin/v1/site/config', { config: { ...siteConfig } });
  }

  function reset() {
    currentPage.value = null;
    activeComponentId.value = null;
    activeSiteConfigItem.value = null;
  }

  return {
    currentPage,
    componentsLibrary,
    activeComponentId,
    activeSiteConfigItem,
    siteConfig,
    pageComponents,
    activeComponent,
    fetchPage,
    fetchComponentsLibrary,
    fetchSiteConfig,
    saveSiteConfig,
    selectSiteConfigItem,
    addComponent,
    removeComponent,
    selectComponent,
    updateComponentConfig,
    reorderComponents,
    saveComponents,
    reset
  };
});
