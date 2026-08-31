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
      // 请求完成即清理强制超时定时器，避免对已结束请求的无效 abort
      const staleConfig = response.config as typeof response.config & { staleTimer?: number };
      if (staleConfig.staleTimer) {
        window.clearTimeout(staleConfig.staleTimer);
      }
      // 请求成功即视为连接已恢复正常，清零超时刷新计数
      sessionStorage.removeItem(STALE_RELOAD_KEY);
      return response.data;
    },
    async onRequest(config) {
      const token = localStg.get('token');
      if (token) {
        Object.assign(config.headers, { Authorization: `Bearer ${token}` });
      }

      // 应用层强制超时兜底：浏览器复用失效 keep-alive 连接时，XHR timeout 计时器可能不触发，
      // 请求会无限挂起（自愈逻辑进不去）。这里用 AbortController 主动中断——进程内操作，
      // 不依赖网络栈超时事件，任何连接状态下都会立即生效。
      const controller = new AbortController();
      const staleConfig = config as typeof config & { staleTimer?: number; staleTimeoutFired?: boolean };
      staleConfig.staleTimer = window.setTimeout(() => {
        staleConfig.staleTimeoutFired = true;
        controller.abort();
      }, REQUEST_TIMEOUT);
      config.signal = controller.signal;

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
      // 请求失败同样清理强制超时定时器
      const staleConfig = error.config as
        | (typeof error.config & { staleTimer?: number; staleTimeoutFired?: boolean })
        | undefined;
      if (staleConfig?.staleTimer) {
        window.clearTimeout(staleConfig.staleTimer);
      }

      // 服务重建/重启后，旧页面连接池仍持有指向旧容器的 keep-alive 连接（half-open），
      // 复用该连接发出的请求会长时间挂起（浏览器 TCP 重传超时可达数分钟）→ 表现为"页面卡死"。
      // 触发自动 reload 自愈的四种识别（任一命中即进入循环，最多 3 次避免死循环）：
      // ① XHR timeout 正常触发（ECONNABORTED + timeout message）
      // ② 失效连接挂起场景 XHR timeout 不触发，由 onRequest 中的 AbortController 强制中断（ERR_CANCELED + staleTimeoutFired 标记）
      // ③ nginx upstream 死 keep-alive 复用，nginx 等待 upstream 超时后返回 5xx（BACKEND_ERROR + 502/503/504）
      // ④ 浏览器到 gateway 的 TCP 连接被 RST 或网络层错误（ERR_NETWORK），常见于容器 SIGKILL 场景
      const isXhrTimeout = error.code === 'ECONNABORTED' && /timeout/i.test(error.message || '');
      const isForcedAbort = error.code === 'ERR_CANCELED' && staleConfig?.staleTimeoutFired === true;
      const isBackendUnavailable =
        error.code === BACKEND_ERROR_CODE && [502, 503, 504].includes(error.response?.status || 0);
      const isNetworkError = error.code === 'ERR_NETWORK';
      if (isXhrTimeout || isForcedAbort || isBackendUnavailable || isNetworkError) {
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
