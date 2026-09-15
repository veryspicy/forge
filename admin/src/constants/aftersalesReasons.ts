/** 后台售后动作原因字典：下拉预设项 + 允许自定义输入（NSelect tag 模式） */

/** 审核拒绝原因（拒绝订单必须填写，写入订单 review 记录） */
export const ORDER_REJECT_REASON_OPTIONS = [
  'Payment not verified',
  'Out of stock / discontinued',
  'Suspected fraudulent order',
  'Invalid or incomplete shipping address',
  'Customer requested cancellation',
  'Other'
]

/** 退款原因 */
export const ORDER_REFUND_REASON_OPTIONS = [
  'Customer requested refund',
  'Returned items received',
  'Damaged or defective item',
  'Duplicate payment',
  'Shipping delay / lost parcel',
  'Goodwill / price adjustment',
  'Other'
]

/** 取消订单原因 */
export const ORDER_CANCEL_REASON_OPTIONS = [
  'Customer requested cancellation',
  'Out of stock / cannot fulfill',
  'Payment not completed in time',
  'Suspected fraudulent order',
  'Other'
]

/** 退款 / 取消的默认原因（可改，保证资金动作始终带审计原因） */
export const ORDER_REFUND_REASON_DEFAULT = ORDER_REFUND_REASON_OPTIONS[0]
export const ORDER_CANCEL_REASON_DEFAULT = ORDER_CANCEL_REASON_OPTIONS[0]

/**
 * C 端退货原因：reason 列自新版起存 code，历史数据存英文文案，
 * 后台统一按当前语言展示；无法识别的原因原样显示（如运营手工内容）。
 */
const RETURN_REASON_LABEL_KEYS: Record<string, string> = {
  damaged: 'page.returns.reasonDamaged',
  wrongitem: 'page.returns.reasonWrongItem',
  notasdescribed: 'page.returns.reasonNotAsDescribed',
  nolongerneeded: 'page.returns.reasonNoLongerNeeded',
  other: 'page.returns.reasonOther',
  // 历史英文文案
  'damaged or defective': 'page.returns.reasonDamaged',
  'wrong item received': 'page.returns.reasonWrongItem',
  'not as described': 'page.returns.reasonNotAsDescribed',
  'no longer needed': 'page.returns.reasonNoLongerNeeded'
}

export function returnReasonLabel(reason: string | null | undefined, t: (key: string) => string): string {
  const raw = String(reason ?? '').trim()
  if (!raw) return '-'
  const key = RETURN_REASON_LABEL_KEYS[raw.toLowerCase()]
  return key ? t(key) : raw
}
