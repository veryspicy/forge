/**
 * Client plugin: apply site-profile theme CSS variables BEFORE first paint.
 *
 * Same rationale as i18n-site.client.ts: do NOT call useSiteProfile() inside a Nuxt plugin
 * (useFetch/useAsyncData unsupported there). Read the serialized payload (site-profile-v5)
 * synchronously and write :root CSS variables once. Runtime theme changes are handled by
 * component-level code (DIY preview etc.).
 */
export default defineNuxtPlugin((nuxtApp) => {
  try {
    const profile = (nuxtApp.payload?.data as any)?.['site-profile-v5'] ?? null
    const theme = profile?.theme
    if (!theme) return

    const STYLE_ID = 'site-theme-vars'

    function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
      return result
        ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16),
          }
        : null
    }

    function rgbToHex(r: number, g: number, b: number): string {
      const toHex = (n: number) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0')
      return `#${toHex(r)}${toHex(g)}${toHex(b)}`
    }

    function lightenHex(hex: string, percent: number): string {
      const rgb = hexToRgb(hex)
      if (!rgb) return hex
      return rgbToHex(rgb.r + (255 - rgb.r) * (percent / 100), rgb.g + (255 - rgb.g) * (percent / 100), rgb.b + (255 - rgb.b) * (percent / 100))
    }

    function darkenHex(hex: string, percent: number): string {
      const rgb = hexToRgb(hex)
      if (!rgb) return hex
      return rgbToHex(rgb.r * (1 - percent / 100), rgb.g * (1 - percent / 100), rgb.b * (1 - percent / 100))
    }

    const vars: Record<string, string> = {}
    if (theme.primaryColor) {
      vars['--color-primary-500'] = theme.primaryColor
      vars['--color-primary-400'] = theme.primaryLight || lightenHex(theme.primaryColor, 10)
      vars['--color-primary-600'] = theme.primaryDark || darkenHex(theme.primaryColor, 10)
    }
    if (theme.secondaryColor) {
      vars['--color-secondary-400'] = theme.secondaryColor
    }
    if (theme.accentColor) {
      vars['--color-accent-500'] = theme.accentColor
    }
    if (theme.fontHeading) {
      vars['--font-heading'] = theme.fontHeading
    }
    if (theme.fontBody) {
      vars['--font-body'] = theme.fontBody
    }
    if (Object.keys(vars).length === 0) return

    let styleEl = document.getElementById(STYLE_ID) as HTMLStyleElement | null
    if (!styleEl) {
      styleEl = document.createElement('style')
      styleEl.id = STYLE_ID
      document.head.appendChild(styleEl)
    }
    const cssText = Object.entries(vars)
      .map(([k, v]) => `${k}: ${v};`)
      .join('\n')
    styleEl.textContent = `:root {\n${cssText}\n}`
  } catch (err) {
    console.warn('[theme-css] plugin error:', err)
  }
})