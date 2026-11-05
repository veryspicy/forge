/**
 * CMS 内容语言选项。
 *
 * 与 C 端 portal-web/nuxt.config.ts 的 i18n.locales 保持一致；
 * 后端最终以站点配置 site_profiles.config.i18n.locales 为准做校验与回退，
 * 此处仅用于 Admin 端录入时的下拉展示。
 */
export interface ContentLocaleOption {
  label: string;
  value: string;
  /** 列表 Tag 展示的简写 */
  short: string;
}

export const contentLocaleOptions: ContentLocaleOption[] = [
  { label: 'English', value: 'en', short: 'EN' },
  { label: '中文', value: 'zh', short: '中文' },
  { label: 'العربية', value: 'ar', short: 'AR' },
  { label: 'Deutsch', value: 'de', short: 'DE' },
  { label: 'Français', value: 'fr', short: 'FR' }
];

/** 下拉组件用选项（仅 label/value） */
export const contentLocaleSelectOptions = contentLocaleOptions.map(({ label, value }) => ({ label, value }));

/** 语言码 -> 列表简写，未知语言回退大写语言码 */
export function contentLocaleShort(locale?: string | null): string {
  const code = String(locale ?? '').toLowerCase();
  return contentLocaleOptions.find(item => item.value === code)?.short ?? (code ? code.toUpperCase() : '-');
}
