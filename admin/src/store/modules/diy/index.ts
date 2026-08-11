import { reactive, ref } from 'vue';
import { defineStore } from 'pinia';
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

/** 选中元素的信息（元素选择模式下从 iframe 中提取） */
export type SelectedElementInfo = {
  elid: string;              // data-marvis-elid UUID，用于精确定位
  selector: string;          // CSS 选择器（人类可读，用于显示）
  tag: string;               // 标签名，如 'DIV'
  id: string;                // id 属性值（可为空）
  classes: string[];         // class 列表
  textContent: string;       // 文本内容（截断到 100 字符）
  rect: { top: number; left: number; width: number; height: number };
  computedStyles: Record<string, string>;
};

/** 站点配置编辑器状态 */
export const useDiyStore = defineStore('diy-store', () => {
  /** 当前选中的站点配置项 key */
  const activeSiteConfigItem = ref<SiteConfigKey | null>(null);
  /** 站点配置数据 */
  const siteConfig = reactive<any>(JSON.parse(JSON.stringify(DEFAULT_SITE_CONFIG)));

  // ========== 元素选择模式状态 ==========
  /** 元素选择模式开关 */
  const elementSelectMode = ref(false);
  /** 当前选中的 iframe 元素信息 */
  const selectedElement = ref<SelectedElementInfo | null>(null);

  // ========== 站点配置方法 ==========
  /** 加载站点配置 */
  async function fetchSiteConfig() {
    try {
      const res = await httpGet('/api/admin/v1/site/config');
      // 后端返回格式：{ "data": configObject } 或 直接返回 configObject
      const data = res.data?.data ?? res.data ?? res;
      if (data && typeof data === 'object') {
        Object.keys(DEFAULT_SITE_CONFIG).forEach(k => {
          if (data[k] !== undefined) {
            siteConfig[k] = JSON.parse(JSON.stringify(data[k]));
          }
        });
      }
    } catch { /* 配置未就绪时使用默认值 */ }
  }

  /** 保存站点配置 */
  async function saveSiteConfig() {
    const res = await httpPut('/api/admin/v1/site/config', { config: { ...siteConfig } });
    // 后端返回格式：{ "data": configObject }
    const data = res.data?.data ?? res.data;
    if (data && typeof data === 'object') {
      Object.keys(DEFAULT_SITE_CONFIG).forEach(k => {
        if (data[k] !== undefined) {
          siteConfig[k] = JSON.parse(JSON.stringify(data[k]));
        }
      });
    }
    return res;
  }

  /** 选择站点配置项 */
  function selectSiteConfigItem(key: SiteConfigKey | null) {
    activeSiteConfigItem.value = key;
    if (key) {
      selectedElement.value = null;
    }
  }

  // ========== 元素选择方法 ==========
  /** 设置元素选择模式 */
  function setElementSelectMode(v: boolean) {
    elementSelectMode.value = v;
  }

  /** 设置当前选中的元素信息（来自 iframe 元素选择回调） */
  function setSelectedElement(el: SelectedElementInfo | null) {
    selectedElement.value = el;
    if (el) {
      activeSiteConfigItem.value = null;
    }
  }

  function reset() {
    activeSiteConfigItem.value = null;
    selectedElement.value = null;
    elementSelectMode.value = false;
  }

  return {
    // 站点配置
    activeSiteConfigItem,
    siteConfig,
    fetchSiteConfig,
    saveSiteConfig,
    selectSiteConfigItem,
    // 元素选择
    elementSelectMode,
    selectedElement,
    setElementSelectMode,
    setSelectedElement,
    reset
  };
});
