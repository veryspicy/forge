export default defineNuxtPlugin((nuxtApp) => {
  try {
    const { profile } = useSiteProfile()
    const i18n = (nuxtApp as any).$i18n as ReturnType<typeof useI18n>

    function isPlainObject(v: unknown): v is Record<string, any> {
      return v !== null && typeof v === 'object' && !Array.isArray(v)
    }

    function deepMerge<T extends Record<string, any>>(target: T, source: Record<string, any>): T {
      const result: Record<string, any> = { ...target }
      for (const key of Object.keys(source)) {
        const srcVal = source[key]
        const tgtVal = result[key]
        if (isPlainObject(srcVal) && isPlainObject(tgtVal)) {
          result[key] = deepMerge(tgtVal, srcVal)
        } else {
          result[key] = srcVal
        }
      }
      return result as T
    }

    function mergeTranslations() {
      if (!i18n) return
      const translations = profile.value?.i18n?.translations
      if (!translations || typeof translations !== 'object') return

      for (const localeKey of Object.keys(translations)) {
        const dict = translations[localeKey]
        if (!dict || typeof dict !== 'object' || Object.keys(dict).length === 0) continue

        try {
          const messages = (i18n as any).messages
          const existing = messages?.value?.[localeKey] || {}
          const merged = deepMerge(existing, dict)
          i18n.setLocaleMessage(localeKey, merged)
        } catch (err) {
          console.warn(`[i18n-site] failed to merge translations for locale "${localeKey}":`, err)
        }
      }
    }

    watch(
      () => profile.value?.i18n?.translations,
      () => {
        mergeTranslations()
      },
      { immediate: true, deep: true },
    )
  } catch (err) {
    console.warn('[i18n-site] plugin error:', err)
  }
})
