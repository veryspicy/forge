import { get, post, patch, del } from './helper';

/** 商品目录 API 封装（分类树 / 轻量品牌 / 商品类型规格模板） */
export const catalogApi = {
  // ---------- 分类树 ----------
  /** 分类树（一级/二级，children 嵌套） */
  listCategories: () => get('/api/admin/v1/catalog/categories'),
  /** 新建分类（parent_id 传一级分类 id 即创建子分类；留空创建一级分类） */
  createCategory: (data: Record<string, any>) => post('/api/admin/v1/catalog/categories', data),
  /** 更新分类 */
  updateCategory: (id: string | number, data: Record<string, any>) =>
    patch(`/api/admin/v1/catalog/categories/${id}`, data),
  /** 删除分类（存在子分类或被商品引用时后端会拒绝） */
  deleteCategory: (id: string | number) => del(`/api/admin/v1/catalog/categories/${id}`),

  // ---------- 轻量品牌 ----------
  listBrands: () => get('/api/admin/v1/catalog/brands'),
  createBrand: (data: Record<string, any>) => post('/api/admin/v1/catalog/brands', data),
  updateBrand: (id: string | number, data: Record<string, any>) => patch(`/api/admin/v1/catalog/brands/${id}`, data),
  deleteBrand: (id: string | number) => del(`/api/admin/v1/catalog/brands/${id}`),

  // ---------- 商品类型 + 规格模板 ----------
  listProductTypes: () => get('/api/admin/v1/catalog/product-types'),
  createProductType: (data: Record<string, any>) => post('/api/admin/v1/catalog/product-types', data),
  updateProductType: (id: string | number, data: Record<string, any>) =>
    patch(`/api/admin/v1/catalog/product-types/${id}`, data),
  deleteProductType: (id: string | number) => del(`/api/admin/v1/catalog/product-types/${id}`)
};
