// Forge — Scroll Reveal Directive (v-reveal)
// Lightweight IntersectionObserver-based reveal with stagger support.
// Respects prefers-reduced-motion: renders final state immediately.
// Registers on both SSR and client so SSR render resolves the directive
// (getSSRProps returns empty props; lifecycle hooks are client-only).
// Usage: v-reveal  or  v-reveal="{ delay: 80 }"
export default defineNuxtPlugin((nuxtApp) => {
  const prefersReduced =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  let observer: IntersectionObserver | null = null
  const tracked = new Map<HTMLElement, () => void>()

  function show(el: HTMLElement) {
    const untrack = tracked.get(el)
    if (untrack) untrack()
    el.classList.add('reveal-in')
  }

  nuxtApp.vueApp.directive('reveal', {
    getSSRProps() {
      // SSR: render element in final visible state, no extra attrs needed.
      return {}
    },
    mounted(el: HTMLElement, binding) {
      if (prefersReduced) {
        el.classList.add('reveal-in')
        return
      }
      const delay = Number(binding.value?.delay) || 0
      if (delay > 0) el.style.setProperty('--reveal-delay', `${delay}ms`)
      el.classList.add('reveal')

      if (!observer) {
        observer = new IntersectionObserver(
          (entries) => {
            for (const entry of entries) {
              if (entry.isIntersecting) show(entry.target as HTMLElement)
            }
          },
          { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
        )
      }
      observer.observe(el)
      tracked.set(el, () => observer?.unobserve(el))
    },
    unmounted(el) {
      const untrack = tracked.get(el)
      if (untrack) untrack()
      tracked.delete(el)
    },
  })
})
