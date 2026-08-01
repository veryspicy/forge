<template>
  <header class="sticky top-0 z-50 bg-neutral-50/95 backdrop-blur shadow-sm">
    <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
      <!-- Brand -->
      <NuxtLink to="/" class="flex items-center gap-2 flex-shrink-0">
        <!-- 动态 Logo（站点配置上传的图片） -->
        <img
          v-if="brandLogo"
          :src="brandLogo"
          :alt="brandName"
          class="h-7 w-auto object-contain"
        />
        <!-- 默认 Logo（SVG 爪印） -->
        <svg
          v-else
          width="28"
          height="28"
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M14 18c-2.5 0-4.5-1.5-5.5-3.5-0.5-1-0.3-2 0.5-2.5 1-0.5 2.5 0 3 1 0.3 0.5 1 1 2 1s1.7-0.5 2-1c0.5-1 2-1.5 3-1 0.8 0.5 1 1.5 0.5 2.5C18.5 16.5 16.5 18 14 18z"
            fill="url(#pawGradient)"
          />
          <ellipse cx="10" cy="11" rx="2.5" ry="3" transform="rotate(-20 10 11)" fill="url(#pawGradient)" />
          <ellipse cx="18" cy="11" rx="2.5" ry="3" transform="rotate(20 18 11)" fill="url(#pawGradient)" />
          <ellipse cx="7" cy="14" rx="2" ry="2.5" transform="rotate(-35 7 14)" fill="url(#pawGradient)" />
          <ellipse cx="21" cy="14" rx="2" ry="2.5" transform="rotate(35 21 14)" fill="url(#pawGradient)" />
          <defs>
            <linearGradient id="pawGradient" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
              <stop stop-color="var(--color-primary-500)" />
              <stop offset="1" stop-color="var(--color-secondary-400)" />
            </linearGradient>
          </defs>
        </svg>
        <span class="text-xl font-heading font-semibold gradient-brand bg-clip-text text-transparent">
          {{ brandName }}
        </span>
      </NuxtLink>

      <!-- Desktop Nav -->
      <nav class="hidden md:flex items-center gap-1">
        <NuxtLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="relative px-3 py-2 text-sm font-medium rounded-md transition-colors"
          :class="
            route.path === link.to
              ? 'text-primary-600'
              : 'text-neutral-600 hover:text-neutral-900'
          "
        >
          {{ link.label }}
          <span
            v-if="route.path === link.to"
            class="absolute bottom-0 left-1/2 -translate-x-1/2 w-5 h-0.5 bg-primary-500 rounded-full"
          />
        </NuxtLink>
      </nav>

      <!-- Right Section -->
      <div class="flex items-center gap-3">
        <!-- Language Select -->
        <select
          v-model="currentLocale"
          class="hidden sm:block text-xs bg-transparent border border-neutral-200 rounded-md px-2 py-1.5 text-neutral-600 focus:outline-none focus:border-primary-400 cursor-pointer"
          @change="onLocaleChange"
        >
          <option value="en">EN</option>
          <option value="zh">ZH</option>
          <option value="ar">AR</option>
          <option value="de">DE</option>
          <option value="fr">FR</option>
        </select>

        <!-- Currency Select -->
        <select
          v-model="currentCurrency"
          class="hidden sm:block text-xs bg-transparent border border-neutral-200 rounded-md px-2 py-1.5 text-neutral-600 focus:outline-none focus:border-primary-400 cursor-pointer"
          @change="onCurrencyChange"
        >
          <option v-for="cur in availableCurrencies" :key="cur" :value="cur">{{ cur }}</option>
        </select>

        <!-- Cart -->
        <NuxtLink
          to="/cart"
          class="relative p-2 text-neutral-600 hover:text-neutral-900 transition-colors"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
          <span
            v-if="cartStore.itemCount > 0"
            class="absolute -top-1 -right-2 bg-accent-500 text-white text-xs rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-0.5 leading-none"
          >
            {{ cartStore.itemCount }}
          </span>
        </NuxtLink>

        <!-- User / Auth -->
        <div class="hidden sm:flex relative" ref="userMenuRef">
          <button
            v-if="!isAuthenticated"
            class="p-2 text-neutral-600 hover:text-neutral-900 transition-colors"
            @click="navigateTo('/login')"
            :title="t('nav.login')"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </button>
          <button
            v-else
            class="flex items-center gap-1.5 px-2 py-1.5 text-sm text-neutral-700 hover:text-neutral-900 rounded-md hover:bg-neutral-100 transition-colors"
            @click="userDropdownOpen = !userDropdownOpen"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span class="max-w-[100px] truncate">{{ user?.name || user?.email }}</span>
          </button>
          <!-- Dropdown -->
          <Transition name="user-dropdown">
            <div
              v-if="isAuthenticated && userDropdownOpen"
              class="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-neutral-200 py-1 z-50"
            >
              <div class="px-4 py-2 border-b border-neutral-100">
                <p class="text-sm font-medium text-neutral-900 truncate">{{ user?.name }}</p>
                <p class="text-xs text-neutral-500 truncate">{{ user?.email }}</p>
              </div>
              <NuxtLink
                to="/orders"
                class="block px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors"
                @click="userDropdownOpen = false"
              >
                {{ t('nav.orders') }}
              </NuxtLink>
              <button
                class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                @click="handleLogout"
              >
                {{ t('nav.logout') }}
              </button>
            </div>
          </Transition>
        </div>

        <!-- Mobile Hamburger -->
        <button
          class="md:hidden p-2 text-neutral-600 hover:text-neutral-900"
          @click="mobileMenuOpen = !mobileMenuOpen"
          aria-label="Toggle menu"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Menu Overlay -->
    <Transition name="mobile-menu">
      <div
        v-if="mobileMenuOpen"
        class="md:hidden fixed inset-0 top-16 bg-neutral-50 z-40 px-4 py-6 flex flex-col gap-6"
      >
        <nav class="flex flex-col gap-2">
          <NuxtLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="text-lg font-medium px-4 py-3 rounded-lg transition-colors"
            :class="
              route.path === link.to
                ? 'bg-primary-50 text-primary-600'
                : 'text-neutral-700 hover:bg-neutral-100'
            "
            @click="mobileMenuOpen = false"
          >
            {{ link.label }}
          </NuxtLink>

          <!-- Mobile Auth Entry -->
          <template v-if="!isAuthenticated">
            <NuxtLink
              to="/login"
              class="text-lg font-medium px-4 py-3 rounded-lg transition-colors text-neutral-700 hover:bg-neutral-100"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.login') }}
            </NuxtLink>
            <NuxtLink
              to="/register"
              class="text-lg font-medium px-4 py-3 rounded-lg transition-colors text-neutral-700 hover:bg-neutral-100"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.register') }}
            </NuxtLink>
          </template>
          <button
            v-else
            class="text-lg font-medium px-4 py-3 rounded-lg transition-colors text-left text-red-600 hover:bg-red-50"
            @click="handleLogout"
          >
            {{ t('nav.logout') }}
          </button>
        </nav>
        <div class="border-t border-neutral-200 pt-4 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <label class="text-sm text-neutral-500">{{ t('nav.language') }}</label>
            <select
              v-model="currentLocale"
              class="text-sm bg-transparent border border-neutral-200 rounded-md px-3 py-2 text-neutral-600 focus:outline-none focus:border-primary-400"
              @change="onLocaleChange"
            >
              <option value="en">EN</option>
              <option value="zh">ZH</option>
              <option value="ar">AR</option>
              <option value="de">DE</option>
              <option value="fr">FR</option>
            </select>
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm text-neutral-500">{{ t('nav.currency') }}</label>
            <select
              v-model="currentCurrency"
              class="text-sm bg-transparent border border-neutral-200 rounded-md px-3 py-2 text-neutral-600 focus:outline-none focus:border-primary-400"
              @change="onCurrencyChange"
            >
              <option v-for="cur in availableCurrencies" :key="cur" :value="cur">{{ cur }}</option>
            </select>
          </div>
        </div>
      </div>
    </Transition>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useCartStore } from '~/stores/cart'
import { useAuth } from '~/composables/useAuth'
import { useCurrency } from '~/composables/useCurrency'
import { useSiteProfile } from '~/composables/useSiteProfile'

const cartStore = useCartStore()
const route = useRoute()
const { locale, setLocale, t } = useI18n()
const { user, isAuthenticated, logout, fetchUser } = useAuth()
const { currency: currentCurrency, setCurrency } = useCurrency()
const { profile, visibleNav } = useSiteProfile()

const mobileMenuOpen = ref(false)
const userDropdownOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)
const currentLocale = ref(locale.value)
watch(locale, (val) => { currentLocale.value = val })

const navLinks = computed(() =>
  visibleNav.value.map((n) => ({
    to: n.to,
    label: t(n.labelKey),
  })),
)

const brandLogo = computed(() => profile.value.brand.logo?.data || null)
const brandName = computed(() => profile.value.brand.name || 'Forge')

const availableCurrencies = computed(() =>
  profile.value.currencies.length > 0 ? profile.value.currencies : ['USD'],
)

function onLocaleChange() {
  setLocale(currentLocale.value)
}

function onCurrencyChange() {
  setCurrency(currentCurrency.value)
}

function handleLogout() {
  logout()
  userDropdownOpen.value = false
  mobileMenuOpen.value = false
}

// Click outside to close dropdown
function onClickOutside(e: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target as Node)) {
    userDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  fetchUser()
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.mobile-menu-enter-active {
  transition: opacity 0.25s ease-out;
}
.mobile-menu-leave-active {
  transition: opacity 0.2s ease-in;
}
.mobile-menu-enter-from,
.mobile-menu-leave-to {
  opacity: 0;
}

.user-dropdown-enter-active {
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}
.user-dropdown-leave-active {
  transition: opacity 0.1s ease-in, transform 0.1s ease-in;
}
.user-dropdown-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.user-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
