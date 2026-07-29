import type { Ref } from 'vue'

const API_BASE = '/api/v1'

export interface AuthUser {
  id: number | string
  email: string
  name: string
  role: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: number | string
  user: AuthUser
}

export interface MeResponse {
  user_id: number | string
  email: string
  name: string
}

export function useAuth() {
  const user = ref<AuthUser | null>(null)
  const token = useCookie<string | null>('forge_token', {
    maxAge: 60 * 60 * 24 * 7,
    sameSite: 'lax',
  })
  const loading = ref(false)

  const isAuthenticated = computed<boolean>(() => !!token.value)
  const isLoading = computed<boolean>(() => loading.value)

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const res = await $fetch<AuthResponse>(`${API_BASE}/auth/login`, {
        method: 'POST',
        body: { email, password },
      })
      token.value = res.access_token
      user.value = res.user
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
  }

  async function register(data: { email: string; password: string; name: string }) {
    loading.value = true
    try {
      const res = await $fetch<AuthResponse>(`${API_BASE}/auth/register`, {
        method: 'POST',
        body: data,
      })
      token.value = res.access_token
      user.value = res.user
      return { success: true }
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    loading.value = true
    try {
      const res = await $fetch<MeResponse>(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token.value}`,
        },
      })
      user.value = {
        id: res.user_id,
        email: res.email,
        name: res.name,
        role: '',
      }
    } catch {
      // token 已失效，清除本地状态
      token.value = null
      user.value = null
    } finally {
      loading.value = false
    }
  }

  return {
    user,
    token,
    loading,
    isLoading,
    isAuthenticated,
    login,
    logout,
    register,
    fetchUser,
  }
}
