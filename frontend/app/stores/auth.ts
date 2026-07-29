// Forge — Auth Store
import { defineStore } from "pinia";
import { useCookie } from "#app";

interface AuthUser {
  id: number | string;
  email: string;
  name: string;
  role: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number | string;
  user: AuthUser;
}

interface MeResponse {
  user_id: number | string;
  email: string;
  name: string;
}

const API_BASE = "/api/v1";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<AuthUser | null>(null);
  const token = useCookie<string | null>("forge_token", {
    maxAge: 60 * 60 * 24 * 7,
    sameSite: "lax",
  });
  const loading = ref(false);

  const isAuthenticated = computed(() => !!token.value);
  const isLoading = computed(() => loading.value);

  async function login(email: string, password: string) {
    loading.value = true;
    try {
      const res = await $fetch<AuthResponse>(`${API_BASE}/auth/login`, {
        method: "POST",
        body: { email, password },
      });
      token.value = res.access_token;
      user.value = res.user;
    } finally {
      loading.value = false;
    }
  }

  async function register(data: {
    email: string;
    password: string;
    name: string;
  }) {
    loading.value = true;
    try {
      const res = await $fetch<AuthResponse>(`${API_BASE}/auth/register`, {
        method: "POST",
        body: data,
      });
      token.value = res.access_token;
      user.value = res.user;
      return { success: true };
    } finally {
      loading.value = false;
    }
  }

  async function fetchUser() {
    if (!token.value) return;
    loading.value = true;
    try {
      const res = await $fetch<MeResponse>(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token.value}` },
      });
      user.value = {
        id: res.user_id,
        email: res.email,
        name: res.name,
        role: "",
      };
    } catch {
      token.value = null;
      user.value = null;
    } finally {
      loading.value = false;
    }
  }

  function logout() {
    token.value = null;
    user.value = null;
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
  };
});
