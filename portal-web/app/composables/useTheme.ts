/**
 * Theme composable — Liquid Glass dark mode.
 * Persists to localStorage ('forge-theme'), applies html.dark class.
 * SSR-safe: only touches document inside effect/mounted paths; initial
 * paint flash is prevented by an inline script in nuxt.config head.
 */
export function useTheme() {
  const STORAGE_KEY = 'forge-theme'

  const theme = ref<'light' | 'dark'>('light')

  function apply(value: 'light' | 'dark') {
    if (import.meta.client) {
      document.documentElement.classList.toggle('dark', value === 'dark')
    }
  }

  function initTheme() {
    if (!import.meta.client) return
    const stored = localStorage.getItem(STORAGE_KEY)
    theme.value = stored === 'dark' ? 'dark' : 'light'
    apply(theme.value)
  }

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, theme.value)
    }
    apply(theme.value)
  }

  // SSR 水合后与初始脚本保持同步
  if (import.meta.client) {
    onMounted(() => {
      const stored = localStorage.getItem(STORAGE_KEY)
      const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
      theme.value = (stored === 'dark' ? 'dark' : current) as 'light' | 'dark'
      apply(theme.value)
    })
  }

  return { theme, initTheme, toggleTheme }
}
