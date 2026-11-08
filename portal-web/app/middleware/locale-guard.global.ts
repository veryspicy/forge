/**
 * 全局语言前缀守卫：把"构建期支持的语言"收敛为"站点实际生效的语言"。
 *
 * 生效语言 = site_profiles.config.i18n 派生（总闸 enabled + 勾选清单 locales）：
 * - 访问未生效语言前缀（如站点只开 en，用户访问 /zh/xxx）→ 302 到默认语言同路径
 * - 根路径 `/` 时若默认语言不是构建期默认（en），直接 302 到 `/<defaultLocale>`
 *
 * 只处理 SSR/首次导航，不参与客户端语言切换（切换器只暴露生效语言）。
 */
export default defineNuxtRouteMiddleware(async (to) => {
  const seg = (to.path.split('/')[1] || '').toLowerCase()
  const isLocalePrefixed = PORTAL_LOCALE_CODES.includes(seg)

  if (!isLocalePrefixed) {
    // 构建期默认语言是 en 时，`/` 的原生行为已正确，无需干预
    if (to.path !== '/') return
    const { active, defaultLocale } = await useActiveSiteLocales()
    const fallback = active[0] ?? defaultLocale
    if (fallback && fallback !== PORTAL_DEFAULT_LOCALE) {
      return navigateTo(`/${fallback}`, { redirectCode: 302 })
    }
    return
  }

  const { active, defaultLocale } = await useActiveSiteLocales()
  if (active.includes(seg)) return

  const target = to.fullPath.replace(/^\/[^/]+/, `/${defaultLocale}`)
  return navigateTo(target, { redirectCode: 302 })
})
