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
  /** 登记外部 URL 为资源（幂等：同站点同 URL 复用已有记录） */
  registerExternal: (params: { url: string; name?: string; fileType?: string; directory?: string; tags?: string[] }) =>
    post('/api/admin/v1/resources/register-external', {
      name: params.name || '',
      url: params.url,
      file_type: params.fileType || undefined,
      directory: params.directory || '',
      tags: params.tags || []
    }),
  /** 列表 */
  list: (params: {
    type?: string;
    siteId?: string;
    keyword?: string;
    directory?: string;
    tag?: string;
    page?: number;
    page_size?: number;
  }) => get('/api/admin/v1/resources', params),
  /** 详情（含引用位置与标签） */
  detail: (id: string) => get(`/api/admin/v1/resources/${id}`),
  /** 重命名 */
  rename: (id: string, name: string) => patch(`/api/admin/v1/resources/${id}`, { name }),
  /** 更新外链 URL（仅 object_key 为空的外链资源；同步刷新引用处商品图地址） */
  updateUrl: (id: string, url: string) => patch(`/api/admin/v1/resources/${id}`, { url }),
  /** 图片编辑替换：裁剪产物上传为新资源，商品引用切到新资源，旧资源保留 */
  replaceImage: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return post(`/api/admin/v1/resources/${id}/replace-image`, form, {
      'Content-Type': 'multipart/form-data'
    });
  },
  /** 目录树 */
  directories: () => get('/api/admin/v1/resources/meta/directories'),
  /** 标签列表 */
  tags: () => get('/api/admin/v1/resources/meta/tags'),
  /** 重名检测 */
  checkName: (name: string, excludeId?: string) =>
    get('/api/admin/v1/resources/check-name', { name, exclude_id: excludeId }),
  /** 批量重名检测（上传前） */
  checkNames: (names: string[]) => post('/api/admin/v1/resources/check-names', { names }),
  /** 回收站列表 */
  trashList: (params: { keyword?: string; fileType?: string; page?: number; page_size?: number }) =>
    get('/api/admin/v1/resources/trash', params),
  /** 恢复（单/批量） */
  restoreTrash: (ids: string[]) => post('/api/admin/v1/resources/trash/restore', { ids }),
  /** 彻底删除（单/批量）：force=true 表示用户已确认引用裂图取舍 */
  purgeTrash: (ids: string[], force = false) => del('/api/admin/v1/resources/trash', { ids, force }),
  /** 清空回收站：force=true 表示用户已确认引用裂图取舍 */
  emptyTrash: (force = false) => del('/api/admin/v1/resources/trash/empty', { force }),
  /** 批量移动到目录 */
  move: (ids: string[], directory: string) => post('/api/admin/v1/resources/move', { ids, directory }),
  /** 全量同步引用关系（商品 / 站点配置表单保存后调用） */
  syncRefs: (params: { refType: string; refId: string; refLabel?: string; resourceIds: string[] }) =>
    post('/api/admin/v1/resources/refs/sync', {
      ref_type: params.refType,
      ref_id: params.refId,
      ref_label: params.refLabel || '',
      resource_ids: params.resourceIds
    }),
  /** 清理无效引用（dryRun=true 仅预览，不删除） */
  cleanupInvalidRefs: (params: { resourceIds?: string[]; dryRun?: boolean }) =>
    post('/api/admin/v1/resources/refs/cleanup', {
      resource_ids: params.resourceIds || [],
      dry_run: params.dryRun ?? false
    }),
  /** 批量打标 */
  setTags: (ids: string[], tags: string[]) => post('/api/admin/v1/resources/tags', { ids, tags }),
  /** 单个软删 */
  remove: (id: string) => del(`/api/admin/v1/resources/${id}`),
  /** 批量软删 */
  batchRemove: (ids: string[]) => del('/api/admin/v1/resources', { ids })
};
