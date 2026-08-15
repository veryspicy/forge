import { get, post, patch, del } from './helper';

/** 资源管理 API 封装 */
export const resourceApi = {
  /** 上传资源 */
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return post('/api/admin/v1/resources/upload', form, {
      'Content-Type': 'multipart/form-data'
    });
  },
  /** 列表 */
  list: (params: { type?: string; siteId?: string; keyword?: string; page?: number; pageSize?: number }) =>
    get('/api/admin/v1/resources', params),
  /** 详情（含引用位置） */
  detail: (id: string) => get(`/api/admin/v1/resources/${id}`),
  /** 重命名 */
  rename: (id: string, name: string) => patch(`/api/admin/v1/resources/${id}`, { name }),
  /** 单个软删 */
  remove: (id: string) => del(`/api/admin/v1/resources/${id}`),
  /** 批量软删 */
  batchRemove: (ids: string[]) => del('/api/admin/v1/resources', { ids })
};
