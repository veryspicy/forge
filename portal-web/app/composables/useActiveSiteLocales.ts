/**
 * 站点**生效**语言（运行期，来自后端 site_profiles.config.i18n）。
 *
 * 与 `useSiteProfile()` 的区别：本 composable 只取 i18n 配置这一小块，
 * 可在 route middleware 中安全调用（不触发翻译合并等副作用），
 * 结果写入 `useState`，SSR 渲染结果随 payload 下发，客户端不会重复请求。
 */
export interface ActiveSiteLocales {
  /** 多语言总闸（i18n.enabled），false 表示单语模式 */
  enabled: boolean
  /** 站点默认语言 */
  defaultLocale: string
  /** 生效语言列表（单语模式只有默认语言一个；首项始终为默认语言） */
  active: string[]
}

function normalise(input: unknown): ActiveSiteLocales {
  const i18n = (input ?? {}) as Record<string, any>
  const enabled = i18n.enabled !== false
  const def = String(i18n.defaultLocale || PORTAL_DEFAULT_LOCALE).toLowerCase()
  const rawList = Array.isArray(i18n.locales) ? i18n.locales : []
  const list: string[] = []
  for (const item of rawList) {
    const code = String(item ?? '').trim().toLowerCase()
    if (code && !list.includes(code)) list.push(code)
  }
  const base = list.length > 0 ? list : [def]
  const active = enabled ? (base.includes(def) ? base : [def, ...base]) : [def]
  return { enabled, defaultLocale: def, active }
}

export async function useActiveSiteLocales(): Promise<ActiveSiteLocales> {
  const cached = useState<ActiveSiteLocales | null>('forge-active-site-locales', () => null)
  if (cached.value) return cached.value

  const runtime = useRuntimeConfig()
  const baseURL = import.meta.server
    ? `${process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'}/api/v1`
    : (runtime.public.apiBase as string)

  const { data } = await useFetch('/site-profile', {
    baseURL,
    key: 'site-i18n-flags',
    server: true,
    lazy: false,
    transform: (raw: any) => normalise(raw?.data?.config?.i18n),
  })

  // 拿不到配置时不拦截任何语言（避免接口抖动导致全站 302）
  const result = data.value ?? { enabled: true, defaultLocale: PORTAL_DEFAULT_LOCALE, active: PORTAL_LOCALE_CODES }
  cached.value = result
  return result
}
