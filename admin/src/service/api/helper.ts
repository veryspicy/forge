import { request } from '../request';

export function get<T = any>(url: string, params?: Record<string, any>) {
  return request<T>({ url, method: 'get', params });
}

export function post<T = any>(url: string, data?: any, headers?: Record<string, string>) {
  return request<T>({ url, method: 'post', data, headers: headers as any });
}

export function patch<T = any>(url: string, data?: any) {
  return request<T>({ url, method: 'patch', data });
}

export function put<T = any>(url: string, data?: any) {
  return request<T>({ url, method: 'put', data });
}

export function del<T = any>(url: string, data?: any) {
  return request<T>({ url, method: 'delete', data });
}
