/**
 * Composable: useSiteProfile
 *
 * Fetches the active Site Profile from the backend and provides
 * reactive brand / theme / navigation / sections / categories data.
 *
 * SSR-safe with built-in request deduplication via useFetch key.
 */
export function useSiteProfile() {
  const config = useRuntimeConfig()

  // SSR 时使用绝对 URL 直接访问后端，避免 Nuxt 内部 server route 代理的上下文问题
  // （特别是 admin iframe 通过 /portal-preview 代理访问时，Nitro 内部调用路径或 Host 头异常导致 API 代理失败）
  // CSR 时使用相对路径：走 admin Vite 代理 / Nuxt server middleware（正常可用）
  const isServerSide = import.meta.server
  const effectiveBase = isServerSide
    ? `${process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'}/api/v1`
    : config.public.apiBase

  const { data, pending, error, refresh } = useFetch('/site-profile', {
    baseURL: effectiveBase,
    key: "site-profile-v4",
    server: true,
    lazy: false,
    transform: (raw: Record<string, any> | null) => {
      // API 返回格式为 {"data": {"id": ..., "config": {actual_profile_fields}}}
      const r = (raw?.data?.config ?? raw?.data ?? raw ?? {}) as Record<string, any>
      return {
        brand: { name: 'Forge', tagline: '', logo: null, ...(r.brand || {}) },
        theme: { primaryColor: '#4f46e5', ...(r.theme || {}) },
        navigation: (r.navigation || []) as NavItem[],
        sections: (r.sections || []) as Section[],
        categories: (r.categories || []) as Category[],
        footer: { columns: ['shop', 'support', 'about', 'legal'], newsletter: true, ...(r.footer || {}) },
        seo: { titleTemplate: '%s | Forge', description: '', ...(r.seo || {}) },
        featureFlags: { show_pets_page: false, show_ai_chat: false, cookie_prefix: 'forge', ...(r.feature_flags || {}) },
        currencies: (r.currencies || ['USD']) as string[],
        i18n: { defaultLocale: 'en', locales: ['en'], ...(r.i18n || {}) },
        regions: (r.regions || []) as string[],
        diyPageSlug: (r.diy_page_slug || '') as string,
      } as SiteProfile
    },
  })

  const defaultProfile: SiteProfile = {
    brand: { name: 'Forge', tagline: '', logo: null },
    theme: { primaryColor: '#4f46e5' },
    navigation: [],
    sections: [],
    categories: [],
    footer: { columns: [], newsletter: false },
    seo: { titleTemplate: '', description: '' },
    featureFlags: {},
    currencies: [],
    i18n: { defaultLocale: 'en', locales: ['en'] },
    regions: [],
    diyPageSlug: '',
  }

  const profile = computed(() => data.value ?? defaultProfile)

  /** Whether a specific feature flag is enabled. */
  function hasFeature(flag: string): boolean {
    return !!(profile.value.featureFlags as Record<string, boolean>)[flag]
  }

  /** Get visible navigation links. */
  const visibleNav = computed(() =>
    profile.value.navigation.filter((n) => n.visible !== false),
  )

  /** Get visible sections. */
  const visibleSections = computed(() =>
    profile.value.sections.filter((s) => s.visible !== false),
  )

  return {
    profile,
    pending,
    error,
    refresh,
    hasFeature,
    visibleNav,
    visibleSections,
  }
}

// ---- Types ----

export interface NavItem {
  key: string
  to: string
  labelKey: string
  visible: boolean
}

export interface Section {
  type: string
  visible: boolean
  config: Record<string, any>
}

export interface Category {
  slug: string
  nameKey: string
  icon: string
}

export interface SiteProfile {
  brand: {
    name: string
    tagline: string
    logo: { type: string; data: string } | null
  }
  theme: {
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
  }
  seo: {
    titleTemplate: string
    description: string
  }
  featureFlags: Record<string, boolean>
  currencies: string[]
  i18n: {
    defaultLocale: string
    locales: string[]
  }
  regions: string[]
  /** DIY 页面 slug — 指向已发布的 DIY 页面作为首页（为空则使用 is_default 页面/硬编码首页） */
  diyPageSlug: string
}
