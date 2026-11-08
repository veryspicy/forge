/**
 * CMS 内容语言选项。
 *
 * 语言清单以站点配置 `site_profiles.config.i18n` 为唯一数据源（后端校验与 C 端路由同源）：
 * - `i18n.enabled` 多语言总闸：false 时站点只保留默认语言（单语模式）
 * - `i18n.locales` 逐语言开关：勾选哪些就生效哪些
 *
 * 下方 `contentLocaleOptions` 只是"已知语言的展示名映射"（label / 简写），
 * 不再当作可用语言清单使用；下拉请走 `buildContentLocaleSelectOptions(i18n)`。
 */
export interface ContentLocaleOption {
  label: string;
  value: string;
  /** 列表 Tag 展示的简写 */
  short: string;
}

/** 站点 i18n 配置的最小结构（site_profiles.config.i18n） */
export interface SiteI18nConfig {
  enabled?: boolean;
  defaultLocale?: string;
  locales?: string[];
}

/** 已知语言的展示名（未知语言码回退大写语言码） */
export const contentLocaleOptions: ContentLocaleOption[] = [
  { label: 'English', value: 'en', short: 'EN' },
  { label: '中文', value: 'zh', short: '中文' },
  { label: 'العربية', value: 'ar', short: 'AR' },
  { label: 'Deutsch', value: 'de', short: 'DE' },
  { label: 'Français', value: 'fr', short: 'FR' }
];

/** 下拉组件用选项（仅 label/value）；静态全集，仅用于无站点配置场景 */
export const contentLocaleSelectOptions = contentLocaleOptions.map(({ label, value }) => ({ label, value }));

/**
 * 按站点配置派生**生效**语言码列表。
 *
 * - 总闸关闭 → 仅默认语言
 * - 总闸打开 → 勾选清单（默认语言缺失时补在最前）
 */
export function resolveActiveLocales(i18n?: SiteI18nConfig | null): string[] {
  const enabled = i18n?.enabled !== false;
  const defaultLocale = String(i18n?.defaultLocale || 'en')
    .trim()
    .toLowerCase();
  const list: string[] = [];
  for (const item of i18n?.locales ?? []) {
    const code = String(item ?? '')
      .trim()
      .toLowerCase();
    if (code && !list.includes(code)) list.push(code);
  }
  const base = list.length > 0 ? list : [defaultLocale];
  if (!enabled) return [defaultLocale];
  return base.includes(defaultLocale) ? base : [defaultLocale, ...base];
}

/** 按站点配置派生下拉选项（label 取已知语言展示名，未知语言码用大写） */
export function buildContentLocaleSelectOptions(i18n?: SiteI18nConfig | null): { label: string; value: string }[] {
  return resolveActiveLocales(i18n).map(code => ({
    label: contentLocaleOptions.find(item => item.value === code)?.label ?? code.toUpperCase(),
    value: code
  }));
}

/** 语言码 -> 列表简写，未知语言回退大写语言码 */
export function contentLocaleShort(locale?: string | null): string {
  const code = String(locale ?? '').toLowerCase();
  return contentLocaleOptions.find(item => item.value === code)?.short ?? (code ? code.toUpperCase() : '-');
}
