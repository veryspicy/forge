/**
 * portal-web 构建期支持的完整语言清单（i18n 静态资源与路由前缀的唯一来源）。
 *
 * 这里定义的是"代码里能渲染哪些语言"；站点**实际生效**哪些语言由后端
 * `site_profiles.config.i18n`（总闸 `enabled` + 勾选清单 `locales`）在运行期决定，
 * 见 `useActiveSiteLocales()` / `useSiteProfile().activeLocales` 与 `middleware/locale-guard`。
 *
 * 新增语言：在此处加一条 + 在 `i18n/locales/` 放对应的 json 文件，即可被站点配置启用。
 */
export interface PortalLocale {
  code: string
  name: string
  file: string
  /** RTL 语言需要显式标注，用于 <html dir> */
  dir?: 'rtl'
}

export const PORTAL_LOCALES: PortalLocale[] = [
  { code: 'en', name: 'English', file: 'en.json' },
  { code: 'zh', name: '中文', file: 'zh.json' },
  { code: 'ar', name: 'العربية', file: 'ar.json', dir: 'rtl' },
  { code: 'de', name: 'Deutsch', file: 'de.json' },
  { code: 'fr', name: 'Français', file: 'fr.json' },
]

/** 构建期支持的语言码（小写） */
export const PORTAL_LOCALE_CODES: string[] = PORTAL_LOCALES.map((l) => l.code)

/** 构建期兜底默认语言（站点配置的 defaultLocale 缺失时使用） */
export const PORTAL_DEFAULT_LOCALE = 'en'
