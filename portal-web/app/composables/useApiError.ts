// Forge — 统一错误解析（C 端）
// 契约见 docs/ERROR-CODE-CONVENTION.md：
// 后端只返回机器码 {code, message, status, errors[]}，UI 层在此收敛为本地化文案，
// 禁止在页面散落直显 err.message / data.detail / HTTP 原文。

interface ApiErrorPayload {
  code?: string
  message?: string
  status?: number
  errors?: Array<{ field?: string; code?: string; message?: string }>
}

export function useApiError() {
  const { t, te } = useI18n()

  /** 从 FetchError/任意异常中解析机器码；无码时按 HTTP 状态兜底 */
  function resolveCode(err: any): string {
    const data = err?.data as ApiErrorPayload | undefined
    if (typeof data?.code === 'string' && data.code) return data.code
    const status: number | undefined = err?.status ?? err?.response?.status
    if (status === 401) return 'UNAUTHORIZED'
    if (status === 403) return 'FORBIDDEN'
    if (status === 404) return 'NOT_FOUND'
    if (status === 409) return 'CONFLICT'
    if (status === 422) return 'VALIDATION_ERROR'
    if (status && status >= 500) return 'SERVER_ERROR'
    if (status) return 'UNKNOWN_ERROR'
    // 无 status/data 视为网络层失败（fetch 拒绝、断网、超时）
    return 'NETWORK_ERROR'
  }

  /** 机器码 -> 当前 locale 文案；语言包缺 key 时兜底通用文案，永不回显机器码 key */
  function localized(code: string): string {
    const key = `errors.${code}`
    return (te(key) ? t(key) : t('errors.UNKNOWN_ERROR')) as string
  }

  function toMessage(err: any): string {
    return localized(resolveCode(err))
  }

  /** 字段级错误（注册/登录等表单定位用）：errors[].field + errors[].code */
  function fieldErrors(err: any): Array<{ field: string; code: string }> {
    const data = err?.data as ApiErrorPayload | undefined
    return (data?.errors ?? []).filter(
      (e): e is { field: string; code: string } => !!e.field && !!e.code
    )
  }

  return { resolveCode, localized, toMessage, fieldErrors }
}
