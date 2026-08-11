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
  /** key = page_type（系统页）或 UUID（自定义页）。
   *  C 端新增的虚拟系统页（/products、/pets、/orders、/chat 等）以 "system_*" 作为 id，
   *  这些页不入库，没有后端 DIY 数据，直接返回占位响应，避免后端因解析不了 UUID 返回 400 并弹错误提示。 */
  getPage: (key: string) => {
    if (typeof key === 'string' && key.startsWith('system_')) {
      // 同步返回一个仿 axios 响应结构的占位结果
      return Promise.resolve({
        data: {
          id: key,
          name: key.replace(/^system_/, ''),
          slug: key.replace(/^system_/, ''),
          title: '',
          description: '',
          page_type: key,
          status: 'draft',
          is_default: false,
          components: [],
          created_at: null,
          updated_at: null,
          published_at: null
        }
      });
    }
    return get(`/api/admin/v1/site/pages/${key}`);
  },
  createPage: (data: { name: string; slug: string; title?: string; description?: string; page_type?: string }) =>
    post('/api/admin/v1/site/custom-pages', data),
  /** key = page_type 或 UUID；后端 _resolve_page 自动处理。
   *  对 system_* 虚拟页直接返回占位成功（这些页不入库）。 */
  updatePage: (key: string, data: Record<string, any>) => {
    if (typeof key === 'string' && key.startsWith('system_')) {
      return Promise.resolve({ data: { id: key, ...data } });
    }
    return put(`/api/admin/v1/site/pages/${key}`, data);
  },
  /** 仅自定义页面可删（后端校验 page_type=custom） */
  deletePage: (id: string) => del(`/api/admin/v1/site/custom-pages/${id}`),
  /** system_* 虚拟页不入库，发布直接返回占位成功。 */
  publishPage: (key: string) => {
    if (typeof key === 'string' && key.startsWith('system_')) {
      return Promise.resolve({ data: { status: 'published' } });
    }
    return post(`/api/admin/v1/site/pages/${key}/publish`);
  },
  /** system_* 虚拟页不入库，取消发布直接返回占位成功。 */
  unpublishPage: (key: string) => {
    if (typeof key === 'string' && key.startsWith('system_')) {
      return Promise.resolve({ data: { status: 'draft' } });
    }
    return post(`/api/admin/v1/site/pages/${key}/unpublish`);
  },
  duplicatePage: (id: string) => post(`/api/admin/v1/site/custom-pages/${id}/duplicate`),
  /** system_* 虚拟页不入库，保存组件直接返回占位成功（组件只存在前端内存中）。 */
  saveComponents: (key: string, data: any[]) => {
    if (typeof key === 'string' && key.startsWith('system_')) {
      return Promise.resolve({ data: { saved: true, count: data.length } });
    }
    return put(`/api/admin/v1/site/pages/${key}/components`, data);
  },
  /** v2.0 无全局默认页概念；设置当前页 is_default。system_* 虚拟页不支持设默认。 */
  setDefault: async (id: string) => {
    if (typeof id === 'string' && id.startsWith('system_')) {
      return Promise.resolve({ data: { id, is_default: false } });
    }
    return put(`/api/admin/v1/site/pages/${id}`, { is_default: true });
  },

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
