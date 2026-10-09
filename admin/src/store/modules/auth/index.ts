import { computed, reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import { useLoading } from '@sa/hooks';
import { fetchGetUserInfo, fetchLogin } from '@/service/api';
import { useRouterPush } from '@/hooks/common/router';
import { localStg } from '@/utils/storage';
import { beginCriticalTransition, endCriticalTransition, markPhase } from '@/utils/stall-watchdog';
import { SetupStoreId } from '@/enum';

export const useAuthStore = defineStore(SetupStoreId.Auth, () => {
  const { toLogin, redirectFromLogin } = useRouterPush(false);
  const { loading: loginLoading, startLoading, endLoading } = useLoading();

  const token = ref(localStg.get('token') || '');

  const userInfo: Api.Auth.UserInfo = reactive({
    userId: '',
    userName: '',
    roles: [],
    permissions: [],
    buttons: []
  });

  /** is super role in static route */
  const isStaticSuper = computed(() => {
    const { VITE_AUTH_ROUTE_MODE, VITE_STATIC_SUPER_ROLE } = import.meta.env;
    return VITE_AUTH_ROUTE_MODE === 'static' && userInfo.roles.includes(VITE_STATIC_SUPER_ROLE);
  });

  /** Is login */
  const isLogin = computed(() => Boolean(token.value));

  /** Reset auth store */
  async function resetStore() {
    markPhase('auth:reset-store');
    localStg.remove('token');
    token.value = '';
    Object.assign(userInfo, { userId: '', userName: '', roles: [], permissions: [], buttons: [] });
    await toLogin();
  }

  async function getUserInfo() {
    markPhase('auth:userinfo:start');
    const { data: info, error } = await fetchGetUserInfo();
    markPhase('auth:userinfo:end', { ok: !error });
    if (!error) {
      Object.assign(userInfo, {
        userId: String(info.id || ''),
        userName: info.email || info.userName || '',
        roles: info.roles || [],
        permissions: info.permissions || [],
        buttons: []
      });
      return true;
    }
    return false;
  }

  /**
   * Login with email and password
   */
  async function login(email: string, password: string, redirect = true) {
    startLoading();
    markPhase('auth:login:start');
    beginCriticalTransition('auth-login');

    try {
      const { data: loginResult, error } = await fetchLogin(email, password);

      if (!error && loginResult.access_token) {
        markPhase('auth:login:token');
        localStg.set('token', loginResult.access_token);
        token.value = loginResult.access_token;

        const pass = await getUserInfo();
        if (pass) {
          markPhase('auth:redirect:start');
          await redirectFromLogin(redirect);
          markPhase('auth:redirect:end');
          window.$notification?.success({
            title: 'Login Success',
            content: `Welcome back, ${userInfo.userName || email}`,
            duration: 3000
          });
        }
      } else {
        resetStore();
      }

      markPhase('auth:login:done');
    } catch (error) {
      markPhase('auth:login:error', { message: (error as Error)?.message?.slice(0, 80) });
      throw error;
    } finally {
      // 无论成功 / 失败 / 抛错都要结束 loading 与关键过渡，避免登录按钮永久停留在加载态
      endCriticalTransition('auth-login');
      endLoading();
    }
  }

  async function initUserInfo() {
    markPhase('auth:init-userinfo:start');
    const savedToken = localStg.get('token');
    if (savedToken) {
      token.value = savedToken;
      const pass = await getUserInfo();
      if (!pass) {
        resetStore();
      }
    }
    markPhase('auth:init-userinfo:end', { hasToken: Boolean(savedToken) });
  }

  return {
    token,
    userInfo,
    isStaticSuper,
    isLogin,
    loginLoading,
    resetStore,
    login,
    initUserInfo
  };
});
