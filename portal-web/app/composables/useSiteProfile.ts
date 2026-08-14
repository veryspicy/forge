/**
 * Composable: useSiteProfile
 *
 * Fetches the active Site Profile from the backend and provides
 * reactive brand / theme / navigation / sections / categories /
 * footer linkGroups / homeHero(carousel|hero) / i18n translations data.
 *
 * SSR-safe with built-in request deduplication via useFetch key.
 */

/** 把 { 'nav.pets.x': 'xxx' } 这样的平级 dotted key 转成嵌套对象 { nav:{ pets:{x:'xxx'} } }。 */
function dottedToNested(flat: Record<string, string>): Record<string, any> {
  const out: Record<string, any> = {}
  for (const key of Object.keys(flat)) {
    const val = flat[key]
    if (val === undefined || val === null) continue
    const parts = key.split('.').filter((p) => p.length > 0)
    if (parts.length === 0) continue
    let cur: any = out
    for (let i = 0; i < parts.length - 1; i++) {
      const p = parts[i]
      const next = cur[p]
      if (!next || typeof next !== 'object' || Array.isArray(next)) {
        cur[p] = {}
      }
      cur = cur[p]
    }
    cur[parts[parts.length - 1]] = val
  }
  return out
}

/** 两个对象深合并（值为非空纯对象时递归，否则用 source 覆盖），不修改入参。 */
function deepMerge<T extends Record<string, any>>(target: T, source: Record<string, any>): T {
  const result: any = { ...(target ?? ({} as T)) }
  for (const k of Object.keys(source ?? {})) {
    const sv = (source as any)[k]
    const tv = result[k]
    const isPlainObj = (v: any) =>
      v != null && typeof v === 'object' && !Array.isArray(v) && Object.getPrototypeOf(v) === Object.prototype
    if (isPlainObj(sv) && isPlainObj(tv)) {
      result[k] = deepMerge(tv as Record<string, any>, sv as Record<string, any>)
    } else {
      result[k] = sv
    }
  }
  return result as T
}

export function useSiteProfile() {
  const config = useRuntimeConfig()
  const {
    locale,
    setLocale,
    getLocaleMessage,
    setLocaleMessage,
    mergeLocaleMessage,
    t,
  } = useI18n()

  // SSR 时使用绝对 URL 直接访问后端，避免 Nuxt 内部 server route 代理的上下文问题
  const isServerSide = import.meta.server
  const effectiveBase = isServerSide
    ? `${process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'}/api/v1`
    : config.public.apiBase

  const { data, pending, error, refresh } = useFetch('/site-profile', {
    baseURL: effectiveBase,
    key: 'site-profile-v5',
    server: true,
    lazy: false,
    transform: (raw: Record<string, any> | null) => {
      const r = (raw?.data?.config ?? raw?.data ?? raw ?? {}) as Record<string, any>
      const nav = (r.navigation || r.nav || []) as NavItem[]
      return {
        brand: { name: 'Forge', tagline: '', logo: null, ...(r.brand || {}) },
        theme: { preset: 'forge', primaryColor: '#4f46e5', primaryLight: '', primaryDark: '', secondaryColor: '', accentColor: '', fontHeading: 'Inter', fontBody: 'Inter', ...(r.theme || {}) },
        navigation: nav.map((n, i) => ({ ...n, order: n.order ?? i, visible: n.visible ?? true })),
        sections: (r.sections || []) as Section[],
        categories: (r.categories || []).map((c: any, i: number) => ({ ...c, order: c.order ?? i, visible: c.visible ?? true, image: c.image ?? '' })) as Category[],
        footer: {
          columns: ['shop', 'support', 'about', 'legal'],
          newsletter: true,
          copyright: '© 2026 Forge',
          linkGroups: [] as FooterLinkGroup[],
          ...(r.footer || {}),
        },
        seo: { titleTemplate: '%s | Forge', description: '', homeTitle: '', metaKeywords: '', ...(r.seo || {}) },
        featureFlags: { show_pets_page: false, show_ai_chat: false, cookie_prefix: 'forge', ...(r.feature_flags || r.featureFlags || {}) },
        currencies: (r.currencies || ['USD']) as string[],
        i18n: { defaultLocale: 'en', locales: ['en'], translations: {}, ...(r.i18n || {}) },
        regions: (r.regions || []) as string[],
        diyPageSlug: (r.diy_page_slug || r.diyPageSlug || '') as string,
        homeHero: {
          useCarousel: false,
          hero: { titleKey: '', title: '', subtitleKey: '', subtitle: '', cta1LabelKey: '', cta1Label: '', cta1To: '/products', cta2LabelKey: '', cta2Label: '', cta2To: '/pets', backgroundImage: '' },
          carousel: { images: [] as CarouselImage[], autoplay: true, interval: 4000 },
          ...(r.homeHero || {}),
        },
      } as SiteProfile
    },
  })

  const defaultProfile: SiteProfile = {
    brand: { name: 'Forge', tagline: '', logo: null },
    theme: { preset: 'forge', primaryColor: '#4f46e5', primaryLight: '', primaryDark: '', secondaryColor: '', accentColor: '', fontHeading: 'Inter', fontBody: 'Inter' },
    navigation: [],
    sections: [],
    categories: [],
    footer: { columns: [], newsletter: false, copyright: '', linkGroups: [] },
    seo: { titleTemplate: '', description: '', homeTitle: '', metaKeywords: '' },
    featureFlags: {},
    currencies: [],
    i18n: { defaultLocale: 'en', locales: ['en'], translations: {} },
    regions: [],
    diyPageSlug: '',
    homeHero: { useCarousel: false, hero: { titleKey: '', title: '', subtitleKey: '', subtitle: '', cta1LabelKey: '', cta1Label: '', cta1To: '/products', cta2LabelKey: '', cta2Label: '', cta2To: '/pets', backgroundImage: '' }, carousel: { images: [], autoplay: true, interval: 4000 } },
  }

  const profile = computed(() => data.value ?? defaultProfile)

  // 把站点配置 i18n.translations 合并进 vue-i18n 运行时 messages，保证 t(labelKey) 生效。
  // 规则：不使用 setLocaleMessage（会整体覆盖，易在静态默认 JSON 加载完成前被冲掉），
  // 改为按命名空间走 mergeLocaleMessage：每个 ns 单独深合并后单次写入，永不破坏其他 namespace 或默认 key。
  function applyI18nTranslations(i18nCfg: NonNullable<SiteProfile['i18n']>) {
    const translations = i18nCfg.translations ?? {}
    for (const localeCode of Object.keys(translations)) {
      const dict = translations[localeCode] ?? {} as Record<string, string>
      const keys = Object.keys(dict)
      if (keys.length === 0) continue
      try {
        const nested = dottedToNested(dict)
        for (const ns of Object.keys(nested)) {
          const sv = nested[ns]
          try {
            if (sv != null && typeof sv === 'object' && !Array.isArray(sv)) {
              // 对象类型 ns：取当前命名空间对象 + 深合并后整 ns 写入
              const existingNs: Record<string, any> = (getLocaleMessage(localeCode) as any)?.[ns] ?? {}
              const mergedNs = deepMerge(existingNs, sv as Record<string, any>)
              mergeLocaleMessage(localeCode, { [ns]: mergedNs })
            } else {
              // 叶子值：直接单键 merge
              mergeLocaleMessage(localeCode, { [ns]: sv })
            }
          } catch { /* ignore per-namespace error */ }
        }
      } catch {
        // 若某些运行时下 mergeLocaleMessage 不可用，静默跳过
      }
    }
    // 应用站点默认语言（仅在 SSR/Hydration 首次或当前 locale 为空时切，以免覆盖用户手动切换）
    const desired = i18nCfg.defaultLocale
    if (desired && typeof setLocale === 'function') {
      const cur = (locale as unknown as { value?: string })?.value ?? ''
      if (!cur || cur === 'en') {
        try { setLocale(desired as Parameters<typeof setLocale>[0]) } catch { /* ignore */ }
      }
    }
    // 刷新 t() 依赖链：在 messages (reactive) 上触发一次读取让 computed 重新求值
    try { t('nav.home') } catch { /* ignore */ }
  }

  // data / locale 任一变化都重新合并 translations（切换语言需要把对应 locale 的站点翻译合并进运行时）。
  // 客户端额外在 nextTick 再执行一次，保证 @nuxtjs/i18n 插件把默认 JSON 加载完成后再合并站点翻译，
  // 避免时序问题：默认消息后加载会覆盖我们先写入的命名空间。
  watch(
    [() => data.value, () => (locale as unknown as { value?: string })?.value],
    ([v]) => {
      if (!v) return
      const run = () => applyI18nTranslations(v.i18n)
      run()
      if (import.meta.client) {
        nextTick(run).catch(() => { /* ignore */ })
      }
    },
    { immediate: true, deep: false },
  )

  /** Whether a specific feature flag is enabled. */
  function hasFeature(flag: string): boolean {
    return !!(profile.value.featureFlags as Record<string, boolean>)[flag]
  }

  /** Get visible navigation links (sorted by order). */
  // 联动过滤：导航项配置 featureFlag 时，对应开关关闭则整项隐藏（如 show_pets_page=false 时宠物导航消失）。
  const visibleNav = computed(() =>
    [...profile.value.navigation]
      .filter((n) => n.visible !== false)
      .filter((n) => {
        if (!n.featureFlag) return true
        return hasFeature(n.featureFlag)
      })
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
  )

  /** Get visible sections (sorted by order). */
  const visibleSections = computed(() =>
    [...profile.value.sections]
      .filter((s) => s.visible !== false)
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
  )

  /** Get visible categories (sorted by order). */
  const visibleCategories = computed(() =>
    [...profile.value.categories]
      .filter((c) => c.visible !== false)
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
  )

  /** Get visible footer link groups (sorted by order). */
  const visibleFooterLinkGroups = computed(() =>
    [...(profile.value.footer.linkGroups || [])]
      .filter((g) => g.visible !== false)
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map((g) => ({
        ...g,
        links: (g.links || []).filter((l) => l.visible !== false),
      })),
  )

  return {
    profile,
    pending,
    error,
    refresh,
    hasFeature,
    visibleNav,
    visibleSections,
    visibleCategories,
    visibleFooterLinkGroups,
  }
}

// ---- Types ----

export interface NavItem {
  key: string
  to: string
  labelKey: string
  label?: string
  visible: boolean
  order?: number
  /** 联动功能开关：配置后该导航项显隐由 featureFlags[featureFlag] 控制 */
  featureFlag?: string
}

export interface Section {
  type: string
  visible: boolean
  order?: number
  config: Record<string, any>
}

export interface Category {
  slug: string
  nameKey: string
  name?: string
  icon: string
  image?: string
  visible?: boolean
  order?: number
}

export interface FooterLinkItem {
  labelKey: string
  label?: string
  to: string
  visible: boolean
}

export interface FooterLinkGroup {
  key: string
  titleKey: string
  title?: string
  visible: boolean
  order?: number
  links: FooterLinkItem[]
}

export interface CarouselImage {
  url: string
  alt?: string
  link?: string
  title?: string
}

export interface SiteProfile {
  brand: {
    name: string
    tagline: string
    logo: { type: string; data: string } | null
  }
  theme: {
    preset: string
    primaryColor: string
    primaryLight?: string
    primaryDark?: string
    secondaryColor?: string
    accentColor?: string
    fontHeading?: string
    fontBody?: string
  }
  navigation: NavItem[]
  sections: Section[]
  categories: Category[]
  footer: {
    columns: string[]
    newsletter: boolean
    copyright?: string
    linkGroups: FooterLinkGroup[]
  }
  seo: {
    titleTemplate: string
    description: string
    homeTitle?: string
    metaKeywords?: string
  }
  featureFlags: Record<string, boolean>
  currencies: string[]
  i18n: {
    defaultLocale: string
    locales: string[]
    translations?: Record<string, Record<string, string>>
  }
  regions: string[]
  diyPageSlug: string
  homeHero: {
    useCarousel: boolean
    hero: {
      titleKey: string
      title: string
      subtitleKey: string
      subtitle: string
      cta1LabelKey: string
      cta1Label: string
      cta1To: string
      cta2LabelKey: string
      cta2Label: string
      cta2To: string
      backgroundImage: string
    }
    carousel: {
      images: CarouselImage[]
      autoplay: boolean
      interval: number
    }
  }
}
