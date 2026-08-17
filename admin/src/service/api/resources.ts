import { get, post, patch, del } from './helper';

/** 资源管理 API 封装 */
export const resourceApi = {
  /** 上传资源 */
  upload: (file: File, options?: { directory?: string; tags?: string[] }) => {
    const form = new FormData();
    form.append('file', file);
    if (options?.directory) form.append('directory', options.directory);
    if (options?.tags?.length) {
      options.tags.forEach(t => form.append('tags', t));
    }
    return post('/api/admin/v1/resources/upload', form, {
      'Content-Type': 'multipart/form-data'
    });
  },
  /** 列表 */
  list: (params: { type?: string; siteId?: string; keyword?: string; directory?: string; tag?: string; page?: number; pageSize?: number }) =>
    get('/api/admin/v1/resources', params),
  /** 详情（含引用位置与标签） */
  detail: (id: string) => get(`/api/admin/v1/resources/${id}`),
  /** 重命名 */
  rename: (id: string, name: string) => patch(`/api/admin/v1/resources/${id}`, { name }),
  /** 目录树 */
  directories: () => get('/api/admin/v1/resources/meta/directories'),
  /** 标签列表 */
  tags: () => get('/api/admin/v1/resources/meta/tags'),
  /** 重名检测 */
  checkName: (name: string, excludeId?: string) =>
    get('/api/admin/v1/resources/check-name', { name, exclude_id: excludeId }),
  /** 批量移动到目录 */
  move: (ids: string[], directory: string) => post('/api/admin/v1/resources/move', { ids, directory }),
  /** 批量打标 */
  setTags: (ids: string[], tags: string[]) => post('/api/admin/v1/resources/tags', { ids, tags }),
  /** 单个软删 */
  remove: (id: string) => del(`/api/admin/v1/resources/${id}`),
  /** 批量软删 */
  batchRemove: (ids: string[]) => del('/api/admin/v1/resources', { ids })
};
