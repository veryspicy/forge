import { del, get, post, put } from './helper';

/** DIY 页面装修 API 封装 */
export const diyApi = {
  // ---------- 页面 ----------
  listPages: (params?: Record<string, any>) => get('/api/admin/v1/diy/pages', params),
  getPage: (id: string) => get(`/api/admin/v1/diy/pages/${id}`),
  createPage: (data: { name: string; slug: string; title?: string; description?: string; page_type?: string }) =>
    post('/api/admin/v1/diy/pages', data),
  updatePage: (id: string, data: Record<string, any>) => put(`/api/admin/v1/diy/pages/${id}`, data),
  deletePage: (id: string) => del(`/api/admin/v1/diy/pages/${id}`),
  publishPage: (id: string) => post(`/api/admin/v1/diy/pages/${id}/publish`),
  unpublishPage: (id: string) => post(`/api/admin/v1/diy/pages/${id}/unpublish`),
  duplicatePage: (id: string) => post(`/api/admin/v1/diy/pages/${id}/duplicate`),
  saveComponents: (id: string, data: any[]) => put(`/api/admin/v1/diy/pages/${id}/components`, data),
  setDefault: (id: string) => post(`/api/admin/v1/diy/pages/${id}/set-default`),

  // ---------- 组件库 ----------
  getComponents: () => get('/api/admin/v1/diy/components'),

  // ---------- 图片上传 ----------
  uploadImage: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return post('/api/admin/v1/diy/upload-image', form, {
      'Content-Type': 'multipart/form-data'
    });
  }
};
