/**
 * Client plugin: merge site-profile i18n translations into vue-i18n BEFORE first paint.
 *
 * Why: site i18n.translations are runtime data (not part of static locale JSON). On SSR,
 * useSiteProfile merges them before rendering. The client must perform the SAME merge
 * before hydration first paint, otherwise t() misses runtime keys -> Hydration mismatch.
 *
 * Why not call useSiteProfile() here: it internally uses useFetch/useAsyncData, which is
 * unsupported in Nuxt plugin context ("Must be called at the top of a `setup` Function").
 * Instead we read the serialized Nuxt payload (useFetch key: site-profile-v5) synchronously.
 *
 * Merge is additive (mergeLocaleMessage), never replaces static messages, so it does not
 * race with useSiteProfile's component-level merge.
 */
export default defineNuxtPlugin((nuxtApp) => {
  try {
    const profile = (nuxtApp.payload?.data as any)?.['site-profile-v5'] ?? null
    const i18n = (nuxtApp as any).$i18n as { mergeLocaleMessage: (locale: string, msg: Record<string, unknown>) => void } | undefined
    if (!profile || !i18n) return

    const translations = profile.i18n?.translations
    if (!translations || typeof translations !== 'object') return

    const mergeAll = () => {
      for (const localeKey of Object.keys(translations)) {
        const dict = translations[localeKey]
        if (!dict || typeof dict !== 'object' || Object.keys(dict).length === 0) continue
        try {
          i18n.mergeLocaleMessage(localeKey, dict)
        } catch (err) {
          console.warn(`[i18n-site] merge failed for locale "${localeKey}":`, err)
        }
      }
    }

    // 首帧渲染前同步合并（插件执行时机在 app.mount 之前）
    mergeAll()

    // 兜底：部分 locale 的静态 messages 为异步加载（lazy）时，重建后再次合并
    nuxtApp.hook('app:mounted', () => {
      try {
        mergeAll()
      } catch (err) {
        console.warn('[i18n-site] mount-time merge error:', err)
      }
    })
  } catch (err) {
    console.warn('[i18n-site] plugin error:', err)
  }
})