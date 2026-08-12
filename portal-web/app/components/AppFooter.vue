<template>
  <footer data-region="footer" class="bg-neutral-900 text-neutral-300">
    <div class="max-w-7xl mx-auto px-4 py-12">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-8">
        <div v-for="group in visibleFooterLinkGroups" :key="group.key">
          <h4 class="text-sm font-heading font-semibold text-neutral-100 uppercase tracking-wider mb-4">
            {{ safeT(group.titleKey, group.title, group.key) }}
          </h4>
          <ul class="space-y-2.5">
            <li v-for="link in group.links" :key="link.labelKey + link.to">
              <NuxtLink
                :to="localePath(normalizeTo(link.to))"
                class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
              >
                {{ safeT(link.labelKey, link.label) }}
              </NuxtLink>
            </li>
          </ul>
        </div>
      </div>

      <div
        v-if="hasFeature('show_newsletter') || profile.footer.newsletter"
        data-newsletter
        class="mt-12 flex flex-col sm:flex-row items-start sm:items-center gap-4 p-6 rounded-2xl bg-neutral-800/50"
      >
        <div class="flex-shrink-0">
          <h4 class="text-base font-heading font-semibold text-neutral-100">
            {{ t('footer.stayInLoop') }}
          </h4>
          <p class="text-sm text-neutral-400 mt-0.5">
            {{ t('footer.newsletterHint') }}
          </p>
        </div>
        <form class="flex flex-1 w-full gap-2" @submit.prevent="onSubscribe">
          <input
            v-model="email"
            type="email"
            required
            :placeholder="t('footer.enterEmail')"
            class="flex-1 text-sm bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2.5 text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-primary-500 transition-colors"
          />
          <button
            type="submit"
            class="flex-shrink-0 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors"
          >
            {{ t('footer.subscribe') }}
          </button>
        </form>
      </div>

      <div class="border-t border-neutral-800 my-8" />

      <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
        <p data-copyright class="text-sm text-neutral-500">
          {{ profile.footer.copyright || t('footer.copyright') || '© 2026 Forge' }}
        </p>
        <p class="text-sm text-neutral-500">
          {{ t('footer.paymentMethods') }}
        </p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useSiteProfile } from '~/composables/useSiteProfile'

const { t, te } = useI18n()
const localePath = useLocalePath()
const { profile, visibleFooterLinkGroups, hasFeature } = useSiteProfile()
const email = ref('')

// t(missingKey) 返回字符串 key（truthy），|| 回退会失效，必须先 te() 判断存在
function safeT(key: string | undefined, ...fallbacks: (string | undefined)[]): string {
  if (key && te(key)) return t(key)
  for (const f of fallbacks) if (f) return f
  return ''
}

function normalizeTo(to: string): string | { path: string; query: Record<string, string> } {
  if (to.startsWith('/products?')) {
    const [path, queryStr] = to.split('?')
    const query: Record<string, string> = {}
    if (queryStr) {
      queryStr.split('&').forEach((pair) => {
        const [k, v] = pair.split('=')
        if (k) query[k] = v || ''
      })
    }
    return { path, query }
  }
  return to
}

function onSubscribe() {
  email.value = ''
}
</script>
