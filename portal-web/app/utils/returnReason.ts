/**
 * 退货原因字典（C 端）
 * - 提交时只传 code，避免把单语言文案写进数据库（站点支持 en/zh/ar/de/fr）
 * - 展示统一走 returnReasonLabel()，历史数据（早期把英文文案写入 reason）同样可正确本地化
 */
export const RETURN_REASON_CODES = ['damaged', 'wrongItem', 'notAsDescribed', 'noLongerNeeded', 'other'] as const

export type ReturnReasonCode = (typeof RETURN_REASON_CODES)[number]

export const RETURN_REASON_I18N_PREFIX = 'returns.reason'

/** 历史数据兼容：早期版本提交的是英文文案而非 code */
const LEGACY_REASON_TEXT_TO_CODE: Record<string, ReturnReasonCode> = {
  'damaged or defective': 'damaged',
  'wrong item received': 'wrongItem',
  'not as described': 'notAsDescribed',
  'no longer needed': 'noLongerNeeded'
}

/** code / 历史英文文案 -> code；无法识别返回 null（如运营手工填写的内容） */
export function normalizeReturnReasonCode(reason?: string | null): ReturnReasonCode | null {
  const raw = String(reason ?? '').trim()
  if (!raw) return null
  if ((RETURN_REASON_CODES as readonly string[]).includes(raw)) return raw as ReturnReasonCode
  return LEGACY_REASON_TEXT_TO_CODE[raw.toLowerCase()] ?? null
}

/** 原因 -> i18n key；无法识别返回 null */
export function returnReasonI18nKey(reason?: string | null): string | null {
  const code = normalizeReturnReasonCode(reason)
  if (!code) return null
  return `${RETURN_REASON_I18N_PREFIX}${code.charAt(0).toUpperCase()}${code.slice(1)}`
}

/** 原因展示：可识别则按当前语言本地化，否则原样返回 */
export function returnReasonLabel(reason: string | null | undefined, t: (key: string) => string): string {
  const raw = String(reason ?? '').trim()
  if (!raw) return '-'
  const key = returnReasonI18nKey(raw)
  return key ? t(key) : raw
}
