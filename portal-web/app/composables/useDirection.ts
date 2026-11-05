/**
 * 书写方向（LTR / RTL）单一来源。
 *
 * dir 取自 @nuxtjs/i18n locales 定义（ar = rtl，其余默认 ltr），
 * 与 app.vue 注入到 <html lang dir> 的判定保持一致，避免页面内出现第二套判断逻辑。
 */
export function useDirection() {
  const { locale, locales } = useI18n()

  const htmlLangDir = computed<{ lang: string; dir: 'ltr' | 'rtl' }>(() => {
    const code = String(locale.value || '')
    const list = (locales.value ?? []) as Array<{ code?: string; dir?: string }>
    const hit = list.find(item => item?.code === code)
    return { lang: code, dir: hit?.dir === 'rtl' ? 'rtl' : 'ltr' }
  })

  const isRtl = computed(() => htmlLangDir.value.dir === 'rtl')

  return { htmlLangDir, isRtl }
}
