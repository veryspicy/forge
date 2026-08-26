import type { AxiosResponse } from 'axios';
import { BACKEND_ERROR_CODE, createFlatRequest } from '@sa/axios';
import { useAuthStore } from '@/store/modules/auth';
import { localStg } from '@/utils/storage';
import { getServiceBaseURL } from '@/utils/service';
import { $t } from '@/locales';
import type { RequestInstanceState } from './type';

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y';
const { baseURL } = getServiceBaseURL(import.meta.env, isHttpProxy);

/** 服务重启后旧页面复用失效 keep-alive 连接导致请求挂起，超时后自动刷新的防循环计数 key */
const STALE_RELOAD_KEY = 'forge:stale-reload-count';

/** 请求超时上限：服务重建/重启后旧连接失效时，避免请求无限挂起（@sa/axios 默认 10s，显式声明防包默认值变化） */
const REQUEST_TIMEOUT = 10_000;

export const request = createFlatRequest(
  {
    baseURL,
    timeout: REQUEST_TIMEOUT
  },
  {
    defaultState: {
      errMsgStack: []
    } as RequestInstanceState,
    transform(response: AxiosResponse<any>) {
      // 请求成功即视为连接已恢复正常，清零超时刷新计数
      sessionStorage.removeItem(STALE_RELOAD_KEY);
      return response.data;
    },
    async onRequest(config) {
      const token = localStg.get('token');
      if (token) {
        Object.assign(config.headers, { Authorization: `Bearer ${token}` });
      }
      return config;
    },
    isBackendSuccess(_response) {
      // Standard HTTP: 2xx = success, our backend returns data directly without code wrapping
      return true;
    },
    async onBackendFail(_response) {
      return null;
    },
    onError(error) {
      // 服务重建/重启后，旧页面连接池仍持有指向旧容器的 keep-alive 连接（half-open），
      // 复用该连接发出的请求会长时间挂起（浏览器 TCP 重传超时可达数分钟）→ 表现为"页面卡死"。
      // 超时后自动刷新页面以建立新连接；连续 3 次仍失败则停止刷新，仅提示错误。
      if (error.code === 'ECONNABORTED' && /timeout/i.test(error.message || '')) {
        const count = Number(sessionStorage.getItem(STALE_RELOAD_KEY) || '0') + 1;
        sessionStorage.setItem(STALE_RELOAD_KEY, String(count));
        if (count <= 3) {
          window.$message?.warning($t('request.timeoutReloading'));
          window.setTimeout(() => {
            window.location.reload();
          }, 800);
          return;
        }
        sessionStorage.removeItem(STALE_RELOAD_KEY);
      }

      let message = error.message;

      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.detail || error.response?.data?.msg || message;
      } else if (error.response?.data?.detail) {
        // HTTP 状态码错误（如 409 引用冲突）优先展示后端具体原因
        message = error.response.data.detail;
      }

      // Handle 401: extract backend error code and map to i18n
      if (error.response?.status === 401) {
        const authStore = useAuthStore();
        authStore.resetStore();
        const detail = error.response?.data?.detail;
        message = detail ? $t(`errors.${detail}` as App.I18n.I18nKey) : $t('request.logoutMsg');
        window.$message?.error(message);
        return;
      }

      if (!request.state.errMsgStack?.length) {
        request.state.errMsgStack = [];
      }

      const isExist = request.state.errMsgStack.includes(message);
      if (!isExist) {
        request.state.errMsgStack.push(message);
        window.$message?.error(message, {
          onLeave: () => {
            request.state.errMsgStack = request.state.errMsgStack.filter((msg: string) => msg !== message);
          }
        });
      }
    }
  }
);
