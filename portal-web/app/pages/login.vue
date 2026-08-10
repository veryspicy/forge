<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-bold text-gray-900">
          {{ $t('auth.signIn') }}
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ $t('auth.enterCredentials') }}
        </p>
      </div>

      <form class="mt-8 space-y-6" @submit.prevent="handleLogin">
        <div class="rounded-md shadow-sm space-y-4">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">{{ $t('auth.email') }}</label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              class="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="admin@forge.com"
            />
          </div>
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">{{ $t('auth.password') }}</label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              class="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Enter your password"
            />
          </div>
        </div>

        <div v-if="errorMsg" class="bg-red-50 border border-red-200 rounded-md p-3">
          <p class="text-sm text-red-800">{{ errorMsg }}</p>
        </div>

        <div>
          <button
            type="submit"
            :disabled="loading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="mr-2 inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
            {{ loading ? $t('auth.signingIn') : $t('auth.signInButton') }}
          </button>
        </div>

        <div class="text-center">
          <NuxtLink :to="localePath('/register')" class="text-sm text-indigo-600 hover:text-indigo-500">
            {{ $t('auth.noAccount') }}
          </NuxtLink>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import enMessages from '~/i18n/locales/en.json'

const errorsEN: Record<string, string> = enMessages.errors

const localePath = useLocalePath()

definePageMeta({
  layout: false,
})

const authStore = useAuthStore()
const { isAuthenticated, user } = storeToRefs(authStore)
const { login } = authStore
const route = useRoute()
const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

function getRedirectPath(): string {
  const redirect = route.query.redirect as string
  if (redirect) {
    try {
      return decodeURIComponent(redirect)
    } catch {
      return localePath('/')
    }
  }
  const role = user.value?.role
  if (role === 'admin' || role === 'operator') {
    return localePath('/admin')
  }
  return localePath('/')
}

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    if (isAuthenticated.value) {
      await navigateTo(getRedirectPath())
    }
  } catch (err: any) {
    const detail = err?.data?.detail
    errorMsg.value = detail ? (errorsEN[detail] || detail) : (err.message || 'Login failed. Please check your credentials.')
  } finally {
    loading.value = false
  }
}

// Redirect if already logged in
if (isAuthenticated.value) {
  navigateTo(getRedirectPath())
}
</script>
