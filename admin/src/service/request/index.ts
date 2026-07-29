import type { AxiosResponse } from 'axios';
import { BACKEND_ERROR_CODE, createFlatRequest } from '@sa/axios';
import { useAuthStore } from '@/store/modules/auth';
import { localStg } from '@/utils/storage';
import { getServiceBaseURL } from '@/utils/service';
import type { RequestInstanceState } from './type';

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y';
const { baseURL } = getServiceBaseURL(import.meta.env, isHttpProxy);

export const request = createFlatRequest(
  {
    baseURL
  },
  {
    defaultState: {
      errMsgStack: []
    } as RequestInstanceState,
    transform(response: AxiosResponse<any>) {
      return response.data;
    },
    async onRequest(config) {
      const token = localStg.get('token');
      if (token) {
        Object.assign(config.headers, { Authorization: `Bearer ${token}` });
      }
      return config;
    },
    isBackendSuccess(response) {
      // Standard HTTP: 2xx = success, our backend returns data directly without code wrapping
      return true;
    },
    async onBackendFail(_response) {
      return null;
    },
    onError(error) {
      let message = error.message;

      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.detail || error.response?.data?.msg || message;
      }

      // Handle 401: token expired, logout
      if (error.response?.status === 401) {
        const authStore = useAuthStore();
        authStore.resetStore();
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
            request.state.errMsgStack = request.state.errMsgStack.filter(
              (msg: string) => msg !== message
            );
          }
        });
      }
    }
  }
);
