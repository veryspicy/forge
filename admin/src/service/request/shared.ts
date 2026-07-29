import { localStg } from '@/utils/storage';

export function getAuthorization() {
  const token = localStg.get('token');
  const Authorization = token ? `Bearer ${token}` : null;

  return Authorization;
}
