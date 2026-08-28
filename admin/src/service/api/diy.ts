import { post } from './helper';

/** 站点配置 API 封装 */
export const siteApi = {
  // ---------- 图片上传 ----------
  uploadImage: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return post('/api/admin/v1/site/upload-image', form, {
      'Content-Type': 'multipart/form-data'
    });
  }
};
