import { request } from '../request';

/**
 * Login with email and password
 *
 * @param email User email
 * @param password Password
 */
export function fetchLogin(email: string, password: string) {
  return request<{ access_token: string; user: Api.Auth.UserInfo }>({
    url: '/api/admin/v1/auth/login',
    method: 'post',
    data: { email, password }
  });
}

/** Get current user info */
export function fetchGetUserInfo() {
  return request<Api.Auth.UserInfo>({ url: '/api/admin/v1/auth/me' });
}
