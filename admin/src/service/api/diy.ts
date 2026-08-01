import { del, get, post, put } from './helper';

/** DIY 页面装修 API 封装 v2.0 */
export const diyApi = {
  // ---------- 页面 ----------
  /** 分页列表：内部调用 listSitePages 合并 system+custom。
   *  兼容旧 UI：系统页面 id = page_type（"home"/"category"/"product_detail"），
   *  自定义页面 id = UUID。这样 publish/unpublish/save 用 id 即可路由。 */
  async listPages(params?: Record<string, any>) {
    const raw = await get('/api/admin/v1/site/pages');
    const system = (raw.data?.system || []).map((p: any) => ({
      ...p,
      id: p.page_type,
      slug: p.page_type,
    }));
    const custom = raw.data?.custom || [];
    const all = [...system, ...custom];
    let items = all;
    if (params?.page_type) items = items.filter((p: any) => p.page_type === params.page_type);
    if (params?.status) items = items.filter((p: any) => p.status === params.status);
    return { data: { items, total: items.length } };
  },
  /** key = page_type（系统页）或 UUID（自定义页） */
  getPage: (key: string) => get(`/api/admin/v1/site/pages/${key}`),
  createPage: (data: { name: string; slug: string; title?: string; description?: string; page_type?: string }) =>
    post('/api/admin/v1/site/custom-pages', data),
  /** key = page_type 或 UUID；后端 _resolve_page 自动处理 */
  updatePage: (key: string, data: Record<string, any>) => put(`/api/admin/v1/site/pages/${key}`, data),
  /** 仅自定义页面可删（后端校验 page_type=custom） */
  deletePage: (id: string) => del(`/api/admin/v1/site/custom-pages/${id}`),
  publishPage: (key: string) => post(`/api/admin/v1/site/pages/${key}/publish`),
  unpublishPage: (key: string) => post(`/api/admin/v1/site/pages/${key}/unpublish`),
  duplicatePage: (id: string) => post(`/api/admin/v1/site/custom-pages/${id}/duplicate`),
  saveComponents: (key: string, data: any[]) => put(`/api/admin/v1/site/pages/${key}/components`, data),
  /** v2.0 无全局默认页概念；设置当前页 is_default */
  setDefault: async (id: string) => put(`/api/admin/v1/site/pages/${id}`, { is_default: true }),

  // ---------- 组件库 ----------
  getComponents: () => get('/api/admin/v1/site/components'),

  // ---------- 图片上传 ----------
  uploadImage: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return post('/api/admin/v1/site/upload-image', form, {
      'Content-Type': 'multipart/form-data'
    });
  }
};
