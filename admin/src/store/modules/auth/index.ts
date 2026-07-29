import { computed, reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import { useLoading } from '@sa/hooks';
import { fetchGetUserInfo, fetchLogin } from '@/service/api';
import { useRouterPush } from '@/hooks/common/router';
import { localStg } from '@/utils/storage';
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
    localStg.remove('token');
    token.value = '';
    Object.assign(userInfo, { userId: '', userName: '', roles: [], permissions: [], buttons: [] });
    await toLogin();
  }

  async function getUserInfo() {
    const { data: info, error } = await fetchGetUserInfo();
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

    const { data: loginResult, error } = await fetchLogin(email, password);

    if (!error && loginResult.access_token) {
      localStg.set('token', loginResult.access_token);
      token.value = loginResult.access_token;

      const pass = await getUserInfo();
      if (pass) {
        await redirectFromLogin(redirect);
        window.$notification?.success({
          title: 'Login Success',
          content: `Welcome back, ${userInfo.userName || email}`,
          duration: 3000
        });
      }
    } else {
      resetStore();
    }

    endLoading();
  }

  async function initUserInfo() {
    const savedToken = localStg.get('token');
    if (savedToken) {
      token.value = savedToken;
      const pass = await getUserInfo();
      if (!pass) {
        resetStore();
      }
    }
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
