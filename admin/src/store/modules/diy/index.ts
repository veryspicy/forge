import { reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import { get as httpGet, put as httpPut } from '@/service/api/helper';

/** 站点配置项的 key 列表（按用户需求排序） */
export const SITE_CONFIG_ITEMS = [
  { key: 'brand', label: '品牌', icon: 'mdi:tag-text' },
  { key: 'theme', label: '主题', icon: 'mdi:palette' },
  { key: 'navigation', label: '导航', icon: 'mdi:menu' },
  { key: 'categories', label: '分类', icon: 'mdi:shape' },
  { key: 'footer', label: '页脚链接', icon: 'mdi:page-layout-footer' },
  { key: 'homeHero', label: '轮播/英雄图', icon: 'mdi:view-carousel' },
  { key: 'seo', label: 'SEO', icon: 'mdi:magnify' },
  { key: 'i18n', label: 'i18n 多语言', icon: 'mdi:translate' },
  { key: 'featureFlags', label: '功能开关', icon: 'mdi:toggle-switch' },
  { key: 'currencies', label: '货币', icon: 'mdi:cash' },
] as const;

export type SiteConfigKey = (typeof SITE_CONFIG_ITEMS)[number]['key'];

const DEFAULT_SITE_CONFIG = {
  brand: { name: 'Forge', tagline: '', logo: { type: 'text', data: '' } },
  theme: {
    preset: 'forge' as string,
    primaryColor: '#18a058', primaryLight: '#36ad6a', primaryDark: '#0c7a43',
    secondaryColor: '#f0a020', accentColor: '#2080f0', fontHeading: 'Inter', fontBody: 'Inter'
  },
  navigation: [
    { key: 'home', to: '/', labelKey: 'nav.home', label: '首页', visible: true, order: 0 },
    { key: 'products', to: '/products', labelKey: 'nav.products', label: '商品', visible: true, order: 1 },
    { key: 'pets', to: '/pets', labelKey: 'nav.pets', label: '我的宠物', visible: true, order: 2, featureFlag: 'show_pets_page' },
    { key: 'orders', to: '/orders', labelKey: 'nav.orders', label: '订单', visible: true, order: 3 },
    { key: 'chat', to: '/chat', labelKey: 'nav.chat', label: 'AI客服', visible: true, order: 4, featureFlag: 'show_ai_chat' },
  ] as { key: string; to: string; labelKey: string; label: string; visible: boolean; order: number; featureFlag?: string }[],
  categories: [
    { slug: 'cat-food', nameKey: 'cat.food', name: '宠物食品', icon: '🍖', image: '', visible: true, order: 0 },
    { slug: 'toys', nameKey: 'cat.toys', name: '玩具', icon: '🎾', image: '', visible: true, order: 1 },
    { slug: 'health-wellness', nameKey: 'cat.healthWellness', name: '健康护理', icon: '💊', image: '', visible: true, order: 2 },
    { slug: 'accessories', nameKey: 'cat.accessories', name: '配件', icon: '🎀', image: '', visible: true, order: 3 },
  ] as { slug: string; nameKey: string; name: string; icon: string; image: string; visible: boolean; order: number }[],
  footer: {
    copyright: '© 2026 Forge. 版权所有。',
    newsletter: true,
    linkGroups: [
      { key: 'shop', titleKey: 'footer.shop', title: '购物', visible: true, order: 0, links: [
        { labelKey: 'footer.petFood', label: '宠物食品', to: '/products?category=pet-food', visible: true },
        { labelKey: 'footer.toys', label: '玩具', to: '/products?category=toys', visible: true },
        { labelKey: 'footer.healthWellness', label: '健康护理', to: '/products?category=health-wellness', visible: true },
      ] as any[] },
      { key: 'support', titleKey: 'footer.support', title: '帮助', visible: true, order: 1, links: [
        { labelKey: 'footer.faqs', label: '常见问题', to: '/faqs', visible: true },
        { labelKey: 'footer.shippingInfo', label: '配送说明', to: '/shipping', visible: true },
      ] as any[] },
      { key: 'about', titleKey: 'footer.about', title: '关于', visible: true, order: 2, links: [
        { labelKey: 'footer.ourStory', label: '我们的故事', to: '/story', visible: true },
        { labelKey: 'footer.blog', label: '博客', to: '/blog', visible: true },
      ] as any[] },
      { key: 'legal', titleKey: 'footer.legal', title: '法律', visible: true, order: 3, links: [
        { labelKey: 'footer.privacyPolicy', label: '隐私政策', to: '/privacy', visible: true },
        { labelKey: 'footer.termsOfService', label: '服务条款', to: '/terms', visible: true },
      ] as any[] },
    ] as any[],
  },
  seo: { titleTemplate: '%s | Forge', homeTitle: 'Forge - 专业宠物用品商店', description: '', metaKeywords: '' },
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'zh', 'ar', 'de', 'fr'] as string[],
    // 预置默认站点配置引用的所有动态 i18n key（nav./cat./footer.），
    // C 端切换语言时由 useSiteProfile.applyI18nTranslations 合并进 vue-i18n 运行时。
    // 新增语言只需在 locales 数组追加 code，并在 translations 补一份对应文案表（后台 i18n 面板可按语言 Tab 编辑）。
    translations: {
      en: {
        'nav.home': 'Home', 'nav.products': 'Products', 'nav.pets': 'My Pets', 'nav.orders': 'Orders', 'nav.chat': 'AI Chat',
        'cat.food': 'Pet Food', 'cat.toys': 'Toys', 'cat.healthWellness': 'Health & Wellness', 'cat.accessories': 'Accessories',
        'footer.shop': 'Shop', 'footer.support': 'Support', 'footer.about': 'About', 'footer.legal': 'Legal',
        'footer.petFood': 'Pet Food', 'footer.toys': 'Toys', 'footer.healthWellness': 'Health & Wellness',
        'footer.faqs': 'FAQ', 'footer.shippingInfo': 'Shipping Info', 'footer.ourStory': 'Our Story', 'footer.blog': 'Blog',
        'footer.privacyPolicy': 'Privacy Policy', 'footer.termsOfService': 'Terms of Service',
      },
      zh: {
        'nav.home': '首页', 'nav.products': '商品', 'nav.pets': '我的宠物', 'nav.orders': '订单', 'nav.chat': 'AI客服',
        'cat.food': '宠物食品', 'cat.toys': '玩具', 'cat.healthWellness': '健康护理', 'cat.accessories': '配件',
        'footer.shop': '购物', 'footer.support': '帮助', 'footer.about': '关于', 'footer.legal': '法律',
        'footer.petFood': '宠物食品', 'footer.toys': '玩具', 'footer.healthWellness': '健康护理',
        'footer.faqs': '常见问题', 'footer.shippingInfo': '配送说明', 'footer.ourStory': '我们的故事', 'footer.blog': '博客',
        'footer.privacyPolicy': '隐私政策', 'footer.termsOfService': '服务条款',
      },
      de: {
        'nav.home': 'Startseite', 'nav.products': 'Produkte', 'nav.pets': 'Meine Haustiere', 'nav.orders': 'Bestellungen', 'nav.chat': 'KI-Chat',
        'cat.food': 'Tierfutter', 'cat.toys': 'Spielzeug', 'cat.healthWellness': 'Gesundheit & Wohlbefinden', 'cat.accessories': 'Zubehör',
        'footer.shop': 'Shop', 'footer.support': 'Hilfe', 'footer.about': 'Über uns', 'footer.legal': 'Rechtliches',
        'footer.petFood': 'Tierfutter', 'footer.toys': 'Spielzeug', 'footer.healthWellness': 'Gesundheit & Wohlbefinden',
        'footer.faqs': 'FAQ', 'footer.shippingInfo': 'Versandinformationen', 'footer.ourStory': 'Unsere Geschichte', 'footer.blog': 'Blog',
        'footer.privacyPolicy': 'Datenschutzrichtlinie', 'footer.termsOfService': 'Nutzungsbedingungen',
      },
      fr: {
        'nav.home': 'Accueil', 'nav.products': 'Produits', 'nav.pets': 'Mes animaux', 'nav.orders': 'Commandes', 'nav.chat': 'Chat IA',
        'cat.food': 'Aliments pour animaux', 'cat.toys': 'Jouets', 'cat.healthWellness': 'Santé et bien-être', 'cat.accessories': 'Accessoires',
        'footer.shop': 'Boutique', 'footer.support': 'Aide', 'footer.about': 'À propos', 'footer.legal': 'Légal',
        'footer.petFood': 'Aliments pour animaux', 'footer.toys': 'Jouets', 'footer.healthWellness': 'Santé et bien-être',
        'footer.faqs': 'FAQ', 'footer.shippingInfo': 'Informations de livraison', 'footer.ourStory': 'Notre histoire', 'footer.blog': 'Blog',
        'footer.privacyPolicy': 'Politique de confidentialité', 'footer.termsOfService': "Conditions d'utilisation",
      },
      ar: {
        'nav.home': 'الرئيسية', 'nav.products': 'المنتجات', 'nav.pets': 'حيواناتي الأليفة', 'nav.orders': 'الطلبات', 'nav.chat': 'الدردشة الذكية',
        'cat.food': 'طعام الحيوانات الأليفة', 'cat.toys': 'الألعاب', 'cat.healthWellness': 'الصحة والعافية', 'cat.accessories': 'الإكسسوارات',
        'footer.shop': 'المتجر', 'footer.support': 'الدعم', 'footer.about': 'من نحن', 'footer.legal': 'القانون',
        'footer.petFood': 'طعام الحيوانات الأليفة', 'footer.toys': 'الألعاب', 'footer.healthWellness': 'الصحة والعافية',
        'footer.faqs': 'الأسئلة الشائعة', 'footer.shippingInfo': 'معلومات الشحن', 'footer.ourStory': 'قصتنا', 'footer.blog': 'المدونة',
        'footer.privacyPolicy': 'سياسة الخصوصية', 'footer.termsOfService': 'شروط الخدمة',
      },
    } as Record<string, Record<string, string>>,
  },
  featureFlags: {
    show_pets_page: true,
    show_ai_chat: true,
    show_categories_section: true,
    show_featured_products: true,
    show_tailored_pets: true,
    show_ai_teaser: true,
    show_newsletter: true,
    enable_reviews: true,
    enable_wishlist: false,
    enable_live_chat: true,
  } as Record<string, boolean>,
  currencies: ['USD'] as string[],
  homeHero: {
    useCarousel: false,
    hero: {
      titleKey: 'home.heroTitle', title: 'Smart Shopping for Your Pet',
      subtitleKey: 'home.heroDesc', subtitle: 'AI-powered product recommendations tailored to your pet.',
      cta1LabelKey: 'home.shopNow', cta1Label: 'Shop Now', cta1To: '/products',
      cta2LabelKey: 'home.addPet', cta2Label: 'Add Your Pet', cta2To: '/pets',
      backgroundImage: '',
    },
    carousel: {
      images: [] as { url: string; alt: string; link: string; title: string }[],
      autoplay: true,
      interval: 4000,
    },
  },
  sections: [
    { type: 'hero', visible: true, order: 0, config: {} },
    { type: 'categories', visible: true, order: 1, config: {} },
    { type: 'featured_products', visible: true, order: 2, config: {} },
    { type: 'ai_teaser', visible: true, order: 3, config: {} },
  ],
  regions: [] as string[],
  diyPageSlug: '',
};

/** 选中元素的信息（元素选择模式下从 iframe 中提取） */
export type SelectedElementInfo = {
  elid: string;
  selector: string;
  tag: string;
  id: string;
  classes: string[];
  textContent: string;
  rect: { top: number; left: number; width: number; height: number };
  computedStyles: Record<string, string>;
};

/** 主题预设：经典配色方案 */
export const THEME_PRESETS: Record<string, { label: string; swatch: string[]; colors: Partial<typeof DEFAULT_SITE_CONFIG.theme> }> = {
  forge: {
    label: 'Forge 绿 (默认)',
    swatch: ['#18a058', '#36ad6a', '#0c7a43'],
    colors: { preset: 'forge', primaryColor: '#18a058', primaryLight: '#36ad6a', primaryDark: '#0c7a43', secondaryColor: '#f0a020', accentColor: '#2080f0' },
  },
  apple: {
    label: 'Apple 风格',
    swatch: ['#0071e3', '#0077ed', '#0077ed'],
    colors: { preset: 'apple', primaryColor: '#0071e3', primaryLight: '#2997ff', primaryDark: '#0062cc', secondaryColor: '#f5f5f7', accentColor: '#ff3b30' },
  },
  cloudflare: {
    label: 'Cloudflare 橙',
    swatch: ['#f38020', '#faa040', '#c96a15'],
    colors: { preset: 'cloudflare', primaryColor: '#f38020', primaryLight: '#faa040', primaryDark: '#c96a15', secondaryColor: '#1d1d1d', accentColor: '#f59e0b' },
  },
  linear: {
    label: 'Linear 靛青',
    swatch: ['#5e6ad2', '#7d86dd', '#4a56c0'],
    colors: { preset: 'linear', primaryColor: '#5e6ad2', primaryLight: '#7d86dd', primaryDark: '#4a56c0', secondaryColor: '#8e8ea0', accentColor: '#2dd4bf' },
  },
  vercel: {
    label: 'Vercel 黑白',
    swatch: ['#000000', '#111111', '#000000'],
    colors: { preset: 'vercel', primaryColor: '#000000', primaryLight: '#333333', primaryDark: '#000000', secondaryColor: '#eaeaea', accentColor: '#ff0080' },
  },
  stripe: {
    label: 'Stripe 蓝紫',
    swatch: ['#635bff', '#8074ff', '#4b44d9'],
    colors: { preset: 'stripe', primaryColor: '#635bff', primaryLight: '#8074ff', primaryDark: '#4b44d9', secondaryColor: '#00d4ff', accentColor: '#ff80bf' },
  },
  notik: {
    label: 'Notion 灰',
    swatch: ['#2f3437', '#464c50', '#191c1d'],
    colors: { preset: 'notik', primaryColor: '#2f3437', primaryLight: '#464c50', primaryDark: '#191c1d', secondaryColor: '#eb5757', accentColor: '#f7c948' },
  },
  shopify: {
    label: 'Shopify 青',
    swatch: ['#008060', '#009e73', '#006b51'],
    colors: { preset: 'shopify', primaryColor: '#008060', primaryLight: '#009e73', primaryDark: '#006b51', secondaryColor: '#002e25', accentColor: '#fb7185' },
  },
};

/** 站点配置编辑器状态 */
export const useDiyStore = defineStore('diy-store', () => {
  /** 当前选中的站点配置项 key */
  const activeSiteConfigItem = ref<SiteConfigKey | null>(null);
  /** 站点配置数据 */
  const siteConfig = reactive<any>(JSON.parse(JSON.stringify(DEFAULT_SITE_CONFIG)));

  // ========== 元素选择模式状态 ==========
  const elementSelectMode = ref(false);
  const selectedElement = ref<SelectedElementInfo | null>(null);

  // ========== 站点配置方法 ==========
  async function fetchSiteConfig() {
    try {
      const res = await httpGet('/api/admin/v1/site/config');
      const data = res.data?.data ?? res.data ?? res;
      if (data && typeof data === 'object') {
        const defaults = JSON.parse(JSON.stringify(DEFAULT_SITE_CONFIG));
        deepMerge(defaults, data);
        // 同步到 reactive store
        Object.keys(defaults).forEach((k) => {
          siteConfig[k] = JSON.parse(JSON.stringify(defaults[k]));
        });
      }
    } catch {
      /* 配置未就绪时使用默认值 */
    }
  }

  async function saveSiteConfig() {
    // 保存前按 order 字段同步导航顺序，并兜底拼接 nav. 前缀（兼容历史数据/直接编辑漏前缀）
    if (Array.isArray(siteConfig.navigation)) {
      siteConfig.navigation.forEach((n: any, i: number) => {
        n.order = i;
        if (n.labelKey && !String(n.labelKey).trim().startsWith('nav.')) {
          n.labelKey = `nav.${String(n.labelKey).trim().replace(/^\.+/, '')}`;
        }
      });
    }
    if (Array.isArray(siteConfig.categories)) {
      siteConfig.categories.forEach((c: any, i: number) => {
        c.order = i;
        // 分类 i18n key 统一 cat. 前缀（兼容历史 footer. 开头 / 漏前缀数据）
        if (c.nameKey) {
          const k = String(c.nameKey).trim().replace(/^\.+/, '');
          if (k.startsWith('cat.')) { c.nameKey = k; }
          else if (k.startsWith('footer.')) { c.nameKey = `cat.${k.replace(/^footer\./, '')}`; }
          else { c.nameKey = `cat.${k}`; }
        }
      });
    }
    if (siteConfig.footer?.linkGroups) {
      siteConfig.footer.linkGroups.forEach((g: any, i: number) => { g.order = i; });
    }
    const res = await httpPut('/api/admin/v1/site/config', { config: deepClone(siteConfig) });
    const data = res.data?.data ?? res.data;
    if (data && typeof data === 'object') {
      const defaults = JSON.parse(JSON.stringify(DEFAULT_SITE_CONFIG));
      deepMerge(defaults, data);
      Object.keys(defaults).forEach((k) => {
        siteConfig[k] = JSON.parse(JSON.stringify(defaults[k]));
      });
    }
    return res;
  }

  function selectSiteConfigItem(key: SiteConfigKey | null) {
    activeSiteConfigItem.value = key;
    if (key) selectedElement.value = null;
  }

  // ========== 元素选择方法 ==========
  function setElementSelectMode(v: boolean) { elementSelectMode.value = v; }
  function setSelectedElement(el: SelectedElementInfo | null) {
    selectedElement.value = el;
    if (el) activeSiteConfigItem.value = null;
  }
  function reset() {
    activeSiteConfigItem.value = null;
    selectedElement.value = null;
    elementSelectMode.value = false;
  }

  return {
    activeSiteConfigItem, siteConfig, fetchSiteConfig, saveSiteConfig, selectSiteConfigItem,
    elementSelectMode, selectedElement, setElementSelectMode, setSelectedElement, reset,
  };
});

// ---- 工具函数 ----
function deepClone<T>(o: T): T { return JSON.parse(JSON.stringify(o)); }
function deepMerge(base: any, override: any) {
  if (!override || typeof override !== 'object') return;
  for (const k of Object.keys(override)) {
    const v = override[k];
    if (v && typeof v === 'object' && !Array.isArray(v) && base[k] && typeof base[k] === 'object' && !Array.isArray(base[k])) {
      deepMerge(base[k], v);
    } else {
      base[k] = v;
    }
  }
}
