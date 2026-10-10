<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NEmpty,
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NImage,
  NInput,
  NInputNumber,
  NModal,
  NProgress,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NSwitch,
  NTable,
  NTag,
  NUpload,
  useMessage
} from 'naive-ui';
import { useI18n } from 'vue-i18n';
import { get, post, patch, del } from '@/service/api/helper';
import { resourceApi } from '@/service/api/resources';
import { VueDraggable } from 'vue-draggable-plus';
import ProductDetailBlocks from './ProductDetailBlocks.vue';
import ProductImageEditor from './ProductImageEditor.vue';

const route = useRoute();
const { t } = useI18n();
const router = useRouter();
const message = useMessage();
const isEdit = computed(() => !!route.params.id);

const error = ref('');

// 商品审核（PRODUCT-AUDIT-FLOW）：展示留痕 + 快捷审核
const auditInfo = ref<{
  audit_status: string;
  audit_reason: string;
  audit_by: string;
  audited_at: string;
}>({
  audit_status: 'pending',
  audit_reason: '',
  audit_by: '',
  audited_at: ''
});
const showAuditModal = ref(false);
const auditForm = ref<{ action: 'approve' | 'reject'; reason: string }>({
  action: 'approve',
  reason: ''
});

function auditLabel(value: string): string {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '未通过'
  };
  return map[value] ?? value ?? '--';
}

function auditTagType(value: string): 'default' | 'success' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'error'
  };
  return map[value] ?? 'default';
}

function openAuditModal() {
  auditForm.value = {
    action: auditInfo.value.audit_status === 'approved' ? 'reject' : 'approve',
    reason: ''
  };
  showAuditModal.value = true;
}

async function submitAudit() {
  if (!route.params.id) return;
  if (auditForm.value.action === 'reject' && !auditForm.value.reason.trim()) {
    message.warning('拒绝时必须填写审核原因');
    return;
  }
  try {
    const res = await post(`/api/admin/v1/products/${route.params.id}/audit`, {
      action: auditForm.value.action,
      reason: auditForm.value.reason.trim() || null
    });
    const p = (res as any)?.data?.data ?? (res as any)?.data;
    auditInfo.value = {
      audit_status: p.audit_status || 'pending',
      audit_reason: p.audit_reason || '',
      audit_by: p.audit_by || '',
      audited_at: p.audited_at || ''
    };
    message.success(auditForm.value.action === 'approve' ? '审核已通过' : '已拒绝该商品');
    showAuditModal.value = false;
  } catch (err) {
    message.error(String(err));
  }
}
const saving = ref(false);
const uploading = ref(false);

const tagsString = ref('');
const regionsString = ref('');
const statusChange = ref<string | null>(null);

const images = ref<{ key: string; url: string; alt?: string; resourceId?: string; isMain?: boolean }[]>([]);
const pendingFiles = ref<File[]>([]);
const imagesSaving = ref(false);
/** 当前选中的图片下标（点击选中高亮边框，操作集中在选中操作条） */
const selectedIdx = ref<number | null>(null);
/** 图片裁剪弹窗 */
const editorModal = ref({ show: false, idx: -1 });
/** 拖拽排序自动保存节流计时器 */
let imagesSaveTimer: ReturnType<typeof setTimeout> | null = null;

/** 从资源管理跳转携带的高亮资源 id（resourceId 匹配的图片加边框高亮） */
const highlightResource = computed(() => String(route.query.highlight_resource || ''));
const highlightMatched = computed(() =>
  highlightResource.value ? images.value.some(i => String(i.resourceId) === highlightResource.value) : false
);
const highlightEl = ref<HTMLElement | null>(null);
watch(
  [highlightResource, images],
  async () => {
    if (!highlightResource.value) return;
    await nextTick();
    highlightEl.value?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  },
  { flush: 'post' }
);
function clearHighlight() {
  router.replace({ query: {} });
}

const variants = ref<any[]>([]);
const variantModal = ref({ show: false, id: '' });
const variantSaving = ref(false);
const variantForm = ref({
  sku: '',
  name: '',
  specRows: [] as { key: string; value: string }[],
  price: 0,
  cost: 0,
  inventory: 0,
  status: 'active',
  is_default: false
});

const catalogOptions = ref<{
  productTypes: { label: string; value: number }[];
  brands: { label: string; value: number }[];
  categories: { label: string; value: number }[];
}>({
  productTypes: [],
  brands: [],
  categories: []
});

function addSpecRow() {
  variantForm.value.specRows.push({ key: '', value: '' });
}
function removeSpecRow(idx: number) {
  variantForm.value.specRows.splice(idx, 1);
}
function attrsToSpecRows(attrs: Record<string, any> | null | undefined): { key: string; value: string }[] {
  const rows: { key: string; value: string }[] = [];
  for (const [k, v] of Object.entries(attrs ?? {})) rows.push({ key: String(k), value: v == null ? '' : String(v) });
  return rows;
}

const seoScore = ref<any>(null);
const seoLoading = ref(false);
const seoSaving = ref(false);
const seoForm = ref({ title: '', description: '', keywords: '' });

const gradeColor = computed(() => {
  const g = seoScore.value?.grade;
  if (g === 'A') return 'text-green-600';
  if (g === 'B') return 'text-blue-600';
  if (g === 'C') return 'text-orange-500';
  if (g === 'D') return 'text-red-600';
  return '';
});

const gradeTagType = computed(() => {
  const g = seoScore.value?.grade;
  if (g === 'A') return 'success';
  if (g === 'B') return 'info';
  if (g === 'C') return 'warning';
  if (g === 'D') return 'error';
  return 'default';
});

function maxScorePercent(d: any) {
  return Math.round((d.score / d.max) * 100);
}

function dimColor(d: any) {
  if (d.status === 'pass') return '#18a058';
  if (d.status === 'partial') return '#f0a020';
  return '#d03050';
}

async function loadSeoScore() {
  if (!isEdit.value) return;
  seoLoading.value = true;
  try {
    const res = await get(`/api/admin/v1/products/${route.params.id}/seo-score`);
    seoScore.value = res.data?.data ?? res.data ?? null;
  } catch {
    seoScore.value = null;
  } finally {
    seoLoading.value = false;
  }
}

async function saveSeo() {
  seoSaving.value = true;
  try {
    const keywords = seoForm.value.keywords
      .split(',')
      .map((k: string) => k.trim())
      .filter(Boolean);
    await patch(`/api/admin/v1/products/${route.params.id}`, {
      seo_title: seoForm.value.title,
      seo_description: seoForm.value.description,
      seo_keywords: keywords
    });
    error.value = '';
    loadSeoScore();
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'SEO 保存失败';
  } finally {
    seoSaving.value = false;
  }
}

const form = ref({
  sku: '',
  name: '',
  slug: '',
  category: 'FOOD',
  description: '',
  category_id: null as number | null,
  brand_id: null as number | null,
  product_type_id: null as number | null,
  price: 0,
  cost: 0,
  inventory: 0,
  is_ai_generated: false,
  // 履约模式：self=自采购 / dropship=一件代发（必须绑定供应商）
  fulfillment_mode: 'self' as 'self' | 'dropship',
  supplier_id: '' as string,
  supplier_sku: '',
  tags: [] as string[],
  region_availability: [] as string[],
  name_translations: {} as Record<string, string>,
  description_translations: {} as Record<string, string>,
  ai_description_translations: {} as Record<string, string>,
  /** 结构化详情块（字段受后端 DETAIL_BLOCK_FIELDS 白名单约束） */
  detail_blocks: [] as Record<string, any>[]
});

const langOptions = [
  { label: 'English (en)', value: 'en' },
  { label: 'العربية (ar)', value: 'ar' },
  { label: '简体中文 (zh-cn)', value: 'zh-cn' },
  { label: 'Français (fr)', value: 'fr' },
  { label: 'Español (es)', value: 'es' },
  { label: 'Deutsch (de)', value: 'de' }
];

const currentLang = ref('en');
const translationName = ref('');
const translationDesc = ref('');
const translationAi = ref('');

function loadLang(lang: string) {
  translationName.value = form.value.name_translations?.[lang] || '';
  translationDesc.value = form.value.description_translations?.[lang] || '';
  translationAi.value = form.value.ai_description_translations?.[lang] || '';
}

function langStatus(lang: string): boolean {
  return !!(
    form.value.name_translations?.[lang] ||
    form.value.description_translations?.[lang]
  );
}

/** Shopify 模式：以 zh-cn 为基准语言，克隆其名称/描述到目标语言（AI 翻译接入前的一键生成） */
function cloneFromBase(lang: string) {
  const baseName = form.value.name_translations?.['zh-cn'] || form.value.name || '';
  const baseDesc = form.value.description_translations?.['zh-cn'] || form.value.description || '';
  if (lang === 'zh-cn') return;
  syncLang('name');
  syncLang('desc');
  syncLang('ai');
  currentLang.value = lang;
  translationName.value = baseName;
  translationDesc.value = baseDesc;
  syncLang('name');
  syncLang('desc');
}

function switchLang(lang: string) {
  syncLang('name');
  syncLang('desc');
  syncLang('ai');
  currentLang.value = lang;
  loadLang(lang);
}

function syncLang(kind: 'name' | 'desc' | 'ai') {
  const key =
    kind === 'name'
      ? 'name_translations'
      : kind === 'desc'
        ? 'description_translations'
        : 'ai_description_translations';
  form.value[key][currentLang.value] =
    kind === 'name' ? translationName.value : kind === 'desc' ? translationDesc.value : translationAi.value;
}

const categoryOptions = [
  { label: 'Food', value: 'FOOD' },
  { label: 'Toy', value: 'TOY' },
  { label: 'Health', value: 'HEALTH' },
  { label: 'Accessory', value: 'ACCESSORY' },
  { label: 'Service', value: 'SERVICE' }
];

async function loadCatalogOptions() {
  try {
    const [typesRes, brandsRes, catsRes] = await Promise.all([
      get('/api/admin/v1/catalog/product-types'),
      get('/api/admin/v1/catalog/brands'),
      get('/api/admin/v1/catalog/categories')
    ]);
    const types = (typesRes.data?.data ?? typesRes.data ?? []) as any[];
    const brands = (brandsRes.data?.data ?? brandsRes.data ?? []) as any[];
    const cats = (catsRes.data?.data ?? catsRes.data ?? []) as any[];
    catalogOptions.value.productTypes = types.map((x: any) => ({ label: String(x.name || x.id), value: Number(x.id) }));
    catalogOptions.value.brands = brands.map((x: any) => ({ label: String(x.name || x.id), value: Number(x.id) }));
    catalogOptions.value.categories = cats.map((x: any) => ({
      label: x.parent_id ? `${x.parent_name || ''} / ${x.name}` : String(x.name),
      value: Number(x.id)
    }));
  } catch {
    /* 目录选项加载失败不阻塞表单 */
  }
}

const fulfillmentOptions = [
  { label: '自采购（本地库存）', value: 'self' },
  { label: '一件代发（供应商直发）', value: 'dropship' }
];

const supplierOptions = ref<{ label: string; value: string }[]>([]);

async function loadSuppliers() {
  try {
    const res = await get('/api/admin/v1/suppliers/', { page: 1, page_size: 200 });
    const list = (res.data?.items || res.data || []) as any[];
    supplierOptions.value = list
      .filter((s: any) => s.is_active !== false)
      .map((s: any) => ({ label: String(s.name || s.id), value: String(s.id) }));
  } catch {
    /* 供应商选项加载失败不阻塞表单 */
  }
}

const statusOptions = [
  { label: 'Active', value: 'active' },
  { label: 'Draft', value: 'draft' },
  { label: 'Inactive', value: 'inactive' }
];

function updateTags() {
  form.value.tags = tagsString.value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
}
function updateRegions() {
  form.value.region_availability = regionsString.value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
}

onMounted(async () => {
  loadCatalogOptions();
  loadSuppliers();
  if (!isEdit.value) return;
  try {
    const res = await get(`/api/admin/v1/products/${route.params.id}`);
    const p = res.data?.data ?? res.data;
    form.value = {
      sku: p.sku || '',
      name: p.name || '',
      slug: p.slug || '',
      category: p.category || 'FOOD',
      description: p.description || '',
      category_id: p.category_id ?? null,
      brand_id: p.brand_id ?? null,
      product_type_id: p.product_type_id ?? null,
      price: p.price || 0,
      cost: p.cost || 0,
      inventory: p.inventory || 0,
      is_ai_generated: p.is_ai_generated || false,
      fulfillment_mode: (p.fulfillment_mode || 'self') as 'self' | 'dropship',
      supplier_id: p.supplier_id || '',
      supplier_sku: p.supplier_sku || '',
      tags: p.tags || [],
      region_availability: p.region_availability || [],
      name_translations: p.name_translations || {},
      description_translations: p.description_translations || {},
      ai_description_translations: p.ai_description_translations || {},
      detail_blocks: (p.detail_blocks || []) as Record<string, any>[]
    };
    loadLang('en');
    tagsString.value = (p.tags || []).join(', ');
    regionsString.value = (p.region_availability || []).join(', ');
    images.value = (p.images || [])
      .slice()
      .sort((a: any, b: any) => Number(a.sort ?? 0) - Number(b.sort ?? 0))
      .map((i: any) => ({
        key: i.key || '',
        url: i.url || '',
        alt: i.alt || '',
        resourceId: i.resource_id || '',
        isMain: !!i.is_main
      }));
    variants.value = p.variants || [];
    auditInfo.value = {
      audit_status: p.audit_status || 'pending',
      audit_reason: p.audit_reason || '',
      audit_by: p.audit_by || '',
      audited_at: p.audited_at || ''
    };
    seoForm.value = {
      title: p.seo_title || '',
      description: p.seo_description || '',
      keywords: (p.seo_keywords || []).join(', ')
    };
    loadSeoScore();
  } catch {
    error.value = t('common.loadFailed');
  }
});

async function handleUpload({ file: fileItem }: any) {
  uploading.value = true;
  error.value = '';
  const file = fileItem.file as File;

  if (isEdit.value) {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await post(`/api/admin/v1/products/${route.params.id}/upload-image`, formData, {
        'Content-Type': 'multipart/form-data'
      });
      const uploaded = (res.data?.data?.images || res.data?.images || []).slice(-1)[0];
      if (uploaded)
        images.value.push({
          key: uploaded.key || '',
          url: uploaded.url || '',
          alt: uploaded.alt || '',
          resourceId: uploaded.resource_id || ''
        });
    } catch (e: any) {
      error.value = e.response?.data?.detail || t('common.uploadFailed') + ': ' + file.name;
    }
  } else {
    pendingFiles.value.push(file);
    images.value.push({ key: '', url: URL.createObjectURL(file), alt: '' });
  }
  uploading.value = false;
}

async function removeImage(idx: number) {
  if (isEdit.value) {
    const img = images.value[idx];
    if (!img.key) {
      images.value.splice(idx, 1);
      return;
    }
    try {
      await del(`/api/admin/v1/products/${route.params.id}/images/${encodeURIComponent(img.key)}`);
    } catch (e: any) {
      if (e.response?.status !== 404) {
        error.value = e.response?.data?.detail || t('common.deleteFailed');
        return;
      }
    }
  } else {
    pendingFiles.value.splice(idx, 1);
  }
  const wasMain = !!images.value[idx]?.isMain;
  images.value.splice(idx, 1);
  // 主图被删除时由第一张接替（与后端 normalize_images 规则一致）
  if (wasMain && images.value.length) images.value[0].isMain = true;
  if (selectedIdx.value !== null) selectedIdx.value = null;
  if (isEdit.value) onImagesDrop();
}

/** 点击选中图片（再次点击取消选中） */
function selectImage(idx: number) {
  selectedIdx.value = selectedIdx.value === idx ? null : idx;
}

/** 拖拽排序结束后自动保存（节流 400ms，避免连续拖拽频繁请求） */
function onImagesDrop() {
  if (!isEdit.value) return;
  if (imagesSaveTimer) clearTimeout(imagesSaveTimer);
  imagesSaveTimer = setTimeout(() => {
    saveImages();
  }, 400);
}

/** 指定主图：整组唯一（通过选中操作条触发） */
function setMainImage(idx: number) {
  images.value = images.value.map((img, i) => ({ ...img, isMain: i === idx }));
  if (isEdit.value) onImagesDrop();
}

/** 打开裁剪弹窗 */
function openEditor(idx: number) {
  editorModal.value = { show: true, idx };
}

/** 裁剪完成：上传新图并替换当前条目，随后自动保存整组 */
async function onEditorSave(payload: { file: File; dataUrl: string }) {
  if (!isEdit.value) return;
  const idx = editorModal.value.idx;
  if (idx < 0 || !images.value[idx]) return;
  const oldKey = images.value[idx].key;
  uploading.value = true;
  error.value = '';
  try {
    const formData = new FormData();
    formData.append('file', payload.file);
    const res = await post(`/api/admin/v1/products/${route.params.id}/upload-image`, formData, {
      'Content-Type': 'multipart/form-data'
    });
    const uploaded = (res.data?.data?.images || res.data?.images || []).slice(-1)[0];
    if (!uploaded) throw new Error('上传返回为空');
    if (oldKey) {
      try {
        await del(`/api/admin/v1/products/${route.params.id}/images/${encodeURIComponent(oldKey)}`);
      } catch {
        /* 旧图删除失败不阻塞替换 */
      }
    }
    images.value[idx] = {
      key: uploaded.key || '',
      url: payload.dataUrl || uploaded.url || '',
      alt: uploaded.alt || images.value[idx].alt || '',
      resourceId: uploaded.resource_id || '',
      isMain: !!images.value[idx].isMain
    };
    await saveImages();
    images.value[idx].url = uploaded.url || images.value[idx].url || '';
  } catch (e: any) {
    error.value = e.response?.data?.detail || '裁剪图片保存失败';
  } finally {
    uploading.value = false;
    editorModal.value = { show: false, idx: -1 };
  }
}

/** 保存图片整组（排序 / 主图 / alt），拖拽与选中操作后自动触发 */
async function saveImages() {
  if (!isEdit.value || !images.value.length) return;
  imagesSaving.value = true;
  error.value = '';
  try {
    const payload = images.value.map((img, idx) => ({
      key: img.key,
      url: img.url,
      alt: img.alt || '',
      is_main: !!img.isMain,
      sort: idx,
      resource_id: img.resourceId || undefined
    }));
    const res = await patch(`/api/admin/v1/products/${route.params.id}/images`, { images: payload });
    const saved = (res.data?.data?.images || res.data?.images || []) as any[];
    if (Array.isArray(saved) && saved.length) {
      images.value = saved
        .slice()
        .sort((a: any, b: any) => Number(a.sort ?? 0) - Number(b.sort ?? 0))
        .map((i: any) => ({
          key: i.key || '',
          url: i.url || '',
          alt: i.alt || '',
          resourceId: i.resource_id || '',
          isMain: !!i.is_main
        }));
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || '图片保存失败';
  } finally {
    imagesSaving.value = false;
  }
}

/** 组装保存载荷：代发必须绑定供应商；自采购清空供应商字段 */
function buildPayload(): Record<string, any> {
  const payload: Record<string, any> = { ...form.value };
  if (payload.fulfillment_mode === 'dropship') {
    if (!payload.supplier_id) throw new Error('一件代发商品必须绑定供应商');
  } else {
    payload.supplier_id = null;
    payload.supplier_sku = '';
  }
  return payload;
}

async function save() {
  saving.value = true;
  error.value = '';
  syncLang('name');
  syncLang('desc');
  syncLang('ai');
  try {
    const payload = buildPayload();
    if (isEdit.value) {
      await patch(`/api/admin/v1/products/${route.params.id}`, payload);
      await syncProductRefs(String(route.params.id));
    } else {
      // 新建商品时一并上传本地变体（后端 ProductCreate.variants 批量创建）
      payload.variants = variants.value.map(v => ({
        sku: v.sku || '',
        name: v.name || '',
        attributes: v.attributes || {},
        price: v.price ?? 0,
        cost: v.cost ?? 0,
        inventory: v.inventory ?? 0,
        status: v.status || 'active',
        is_default: !!v.is_default
      }));
      const res = await post('/api/admin/v1/products/', payload);
      const newId = res.data?.data?.id ?? res.data?.id;
      for (const file of pendingFiles.value) {
        const formData = new FormData();
        formData.append('file', file);
        const up = await post(`/api/admin/v1/products/${newId}/upload-image`, formData, {
          'Content-Type': 'multipart/form-data'
        });
        const uploaded = (up.data?.data?.images || up.data?.images || []).slice(-1)[0];
        if (uploaded)
          images.value.push({
            key: uploaded.key || '',
            url: uploaded.url || '',
            alt: uploaded.alt || '',
            resourceId: uploaded.resource_id || ''
          });
      }
      await syncProductRefs(String(newId));
    }
    router.push('/products');
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || t('common.saveFailed');
  } finally {
    saving.value = false;
  }
}

/** 保存后同步产品图片资源引用（失败不阻塞保存主流程） */
async function syncProductRefs(productId: string) {
  const resourceIds = images.value.map(i => i.resourceId).filter(Boolean) as string[];
  if (!resourceIds.length) return;
  try {
    await resourceApi.syncRefs({
      refType: 'product',
      refId: productId,
      refLabel: String(form.value.name || `product-${productId}`),
      resourceIds
    });
  } catch {
    /* 引用同步失败仅提示 */
  }
}

async function changeStatus() {
  if (!statusChange.value) return;
  try {
    await post(`/api/admin/v1/products/${route.params.id}/status`, { status: statusChange.value });
    statusChange.value = null;
    router.push('/products');
  } catch (e: any) {
    error.value = e.response?.data?.detail || t('page.productsDetail.statusUpdateFailed');
  }
}

function openVariantModal(v?: any) {
  if (v) {
    variantModal.value.id = v.id;
    variantForm.value = {
      sku: v.sku || '',
      name: v.name || '',
      specRows: attrsToSpecRows(
        v.attributes ?? (v.specs ? Object.fromEntries((v.specs as any[]).map((s: any) => [s.spec_key, s.value])) : null)
      ),
      price: v.price ?? 0,
      cost: v.cost ?? 0,
      inventory: v.inventory ?? 0,
      status: v.status || 'active',
      is_default: !!v.is_default
    };
  } else {
    variantModal.value.id = '';
    variantForm.value = {
      sku: '',
      name: '',
      specRows: [],
      price: 0,
      cost: 0,
      inventory: 0,
      status: 'active',
      is_default: false
    };
  }
  variantModal.value.show = true;
}

async function saveVariant() {
  variantSaving.value = true;
  error.value = '';
  const attributes: Record<string, any> = {};
  for (const row of variantForm.value.specRows) {
    const key = (row.key ?? '').trim();
    if (!key) continue;
    if (key in attributes) {
      error.value = `选项名重复: ${key}`;
      variantSaving.value = false;
      return;
    }
    attributes[key] = (row.value ?? '').trim();
  }
  const payload: any = {
    sku: variantForm.value.sku.trim(),
    name: variantForm.value.name.trim(),
    attributes,
    price: variantForm.value.price,
    cost: variantForm.value.cost,
    inventory: variantForm.value.inventory,
    status: variantForm.value.status,
    is_default: variantForm.value.is_default
  };
  try {
    if (!isEdit.value) {
      // 新建模式：纯本地维护，随商品创建一并上传（后端 ProductCreate.variants）
      if (variantModal.value.id) {
        const idx = variants.value.findIndex(x => String(x.id) === String(variantModal.value.id));
        if (idx >= 0) variants.value[idx] = { ...variants.value[idx], ...payload };
      } else {
        variants.value.push({ id: `local-${Date.now()}`, ...payload });
      }
      variantModal.value.show = false;
      return;
    }
    if (variantModal.value.id) {
      await patch(`/api/admin/v1/products/${route.params.id}/variants/${variantModal.value.id}`, payload);
    } else {
      await post(`/api/admin/v1/products/${route.params.id}/variants`, payload);
    }
    await reloadVariants();
    variantModal.value.show = false;
  } catch (e: any) {
    error.value = e.response?.data?.detail || '变体保存失败';
  } finally {
    variantSaving.value = false;
  }
}

async function deleteVariant(id: string) {
  if (!isEdit.value) {
    variants.value = variants.value.filter(v => String(v.id) !== String(id));
    return;
  }
  try {
    await del(`/api/admin/v1/products/${route.params.id}/variants/${id}`);
    await reloadVariants();
  } catch (e: any) {
    error.value = e.response?.data?.detail || '变体删除失败';
  }
}

async function reloadVariants() {
  const res = await get(`/api/admin/v1/products/${route.params.id}/variants`);
  variants.value = res.data?.data ?? res.data ?? [];
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold m-0">
        {{ isEdit ? t('common.edit') + ' ' + t('common.product') : t('common.new') + ' ' + t('common.product') }}
      </h2>
      <NButton @click="$router.push('/products')">{{ $t('common.backToList') }}</NButton>
    </div>

    <div v-if="error" class="bg-red-50 text-red-600 p-3 rounded text-sm">{{ error }}</div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Basic Info -->
      <NCard :title="$t('common.basicInfo')" size="small" class="md:col-span-2">
        <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.sku')" required><NInput v-model:value="form.sku" /></NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.name')" required><NInput v-model:value="form.name" /></NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.productsDetail.slug')"><NInput v-model:value="form.slug" /></NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.products.category')">
              <NSelect v-model:value="form.category" :options="categoryOptions" />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem label="履约模式">
              <NSelect v-model:value="form.fulfillment_mode" :options="fulfillmentOptions" />
            </NFormItem>
          </NGi>
          <NGi v-if="form.fulfillment_mode === 'dropship'" span="1">
            <NFormItem label="供应商" required>
              <NSelect
                v-model:value="form.supplier_id"
                :options="supplierOptions"
                placeholder="选择供应商"
                clearable
                filterable
              />
            </NFormItem>
          </NGi>
          <NGi v-if="form.fulfillment_mode === 'dropship'" span="1">
            <NFormItem label="供应商 SKU">
              <NInput v-model:value="form.supplier_sku" placeholder="供应商侧货号（可选）" />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem label="商品类型">
              <NSelect
                v-model:value="form.product_type_id"
                :options="catalogOptions.productTypes"
                placeholder="选择规格模板"
                clearable
                filterable
              />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem label="品牌">
              <NSelect
                v-model:value="form.brand_id"
                :options="catalogOptions.brands"
                placeholder="选择品牌"
                clearable
                filterable
              />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem label="分类">
              <NSelect
                v-model:value="form.category_id"
                :options="catalogOptions.categories"
                placeholder="选择分类（二级树）"
                clearable
                filterable
              />
            </NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.description')">
              <NInput v-model:value="form.description" type="textarea" :rows="3" />
            </NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Product Audit -->
      <NCard title="商品审核" size="small" class="md:col-span-2">
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-2">
            <div class="flex items-center gap-3">
              <span class="text-sm text-gray-500">当前状态:</span>
              <NTag size="small" :bordered="false" :type="auditTagType(auditInfo.audit_status)">
                {{ auditLabel(auditInfo.audit_status) }}
              </NTag>
            </div>
            <div class="flex items-center gap-3 text-sm text-gray-500">
              <span>审核人: {{ auditInfo.audit_by || '--' }}</span>
              <span>审核时间: {{ auditInfo.audited_at || '--' }}</span>
            </div>
            <div v-if="auditInfo.audit_reason" class="text-sm text-gray-500">
              <span class="mr-1">审核备注:</span>{{ auditInfo.audit_reason }}
            </div>
          </div>
          <NButton v-if="isEdit" size="small" type="primary" secondary @click="openAuditModal">审核</NButton>
        </div>
      </NCard>

      <!-- Translations -->
      <NCard title="多语言内容" size="small" class="md:col-span-2">
        <NFormItem label="语言">
          <NSelect :value="currentLang" :options="langOptions" style="width: 200px" @update:value="switchLang" />
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="opt in langOptions"
              :key="opt.value"
              type="button"
              class="rounded px-2.5 py-1 text-xs transition"
              :class="
                currentLang === opt.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
              "
              :title="opt.label"
              @click="switchLang(opt.value)"
            >
              {{ opt.value }}
              <span :class="langStatus(opt.value) ? 'text-green-400' : 'text-amber-400'">●</span>
            </button>
          </div>
        </NFormItem>
        <div class="mb-2 flex items-center gap-2">
          <NButton size="small" type="primary" secondary @click="cloneFromBase(currentLang)">
            从基准语言(zh-cn)克隆
          </NButton>
          <NButton size="small" disabled title="需配置 AI 服务后启用：将基准语言内容翻译为目标语言">
            AI 翻译（待接入）
          </NButton>
          <span class="text-xs text-gray-400">● 绿=已填写，黄=未翻译（C 端自动回退基准语言）</span>
        </div>
        <NGrid :cols="2" :x-gap="16" responsive="screen">
          <NGi span="2">
            <NFormItem label="名称翻译">
              <NInput v-model:value="translationName" @update:value="syncLang('name')" />
            </NFormItem>
          </NGi>
          <NGi span="2">
            <NFormItem label="描述翻译">
              <NInput v-model:value="translationDesc" type="textarea" :rows="3" @update:value="syncLang('desc')" />
            </NFormItem>
          </NGi>
          <NGi span="2">
            <NFormItem label="AI 描述翻译">
              <NInput v-model:value="translationAi" type="textarea" :rows="3" @update:value="syncLang('ai')" />
            </NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Pricing -->
      <NCard :title="$t('page.pricing.title')" size="small">
        <NFormItem :label="$t('page.products.price')">
          <NInputNumber v-model:value="form.price" :min="0" :step="0.01" style="width: 100%" />
        </NFormItem>
        <NFormItem :label="$t('common.cost')">
          <NInputNumber v-model:value="form.cost" :min="0" :step="0.01" style="width: 100%" />
        </NFormItem>
      </NCard>

      <!-- Inventory -->
      <NCard :title="$t('common.inventory')" size="small">
        <NFormItem :label="$t('page.productsDetail.inventory')">
          <NInputNumber v-model:value="form.inventory" :min="0" style="width: 100%" />
        </NFormItem>
        <NFormItem :label="$t('page.productsDetail.aiGenerated')">
          <NSwitch v-model:value="form.is_ai_generated" />
        </NFormItem>
      </NCard>

      <!-- Tags & Regions -->
      <NCard :title="$t('common.tagsRegions')" size="small" class="md:col-span-2">
        <NGrid :cols="2" :x-gap="16" responsive="screen">
          <NGi span="1 m:2">
            <NFormItem :label="$t('page.productsDetail.tagsComma')">
              <NInput v-model:value="tagsString" @update:value="updateTags" />
            </NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('page.productsDetail.regionsComma')">
              <NInput v-model:value="regionsString" @update:value="updateRegions" />
            </NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Images -->
      <NCard :title="$t('common.productImages')" size="small" class="md:col-span-2">
        <div
          v-if="highlightResource"
          class="mb-3 flex items-center justify-between gap-2 rounded bg-green-50 px-3 py-2 text-xs text-green-600 dark:bg-green-900/20 dark:text-green-300"
        >
          <span>{{ highlightMatched ? '已定位到引用图片（绿色边框高亮）' : '未在当前图片列表中找到该引用图片' }}</span>
          <NButton size="tiny" quaternary @click="clearHighlight">清除高亮</NButton>
        </div>
        <div v-if="images.length" class="mb-4">
          <div class="flex flex-wrap gap-3">
            <VueDraggable
              v-model="images"
              :item-key="(item: any) => item.key || item.url"
              :animation="150"
              ghost-class="opacity-40"
              @end="onImagesDrop"
            >
              <template #item="{ element: img, index: idx }">
                <div
                  class="relative w-[140px] rounded-md overflow-hidden border transition-all duration-300 cursor-pointer select-none"
                  :class="
                    selectedIdx === idx
                      ? 'ring-2 ring-blue-500 border-blue-500'
                      : String(img.resourceId) === highlightResource
                        ? 'ring-2 ring-green-500 border-green-500'
                        : 'border-[var(--n-border-color)]'
                  "
                  @click="selectImage(idx)"
                >
                  <div class="relative">
                    <NImage :src="img.url" width="140" height="140" style="object-fit: cover" />
                    <NTag v-if="img.isMain" size="tiny" type="success" class="absolute top-0.5 left-0.5">主图</NTag>
                    <NButton
                      class="absolute top-0.5 right-0.5"
                      size="tiny"
                      circle
                      type="error"
                      @click.stop="removeImage(idx)"
                    >
                      &times;
                    </NButton>
                  </div>
                  <div class="px-1 py-1 text-center text-xs">
                    {{ img.alt || '无 alt' }}
                  </div>
                </div>
              </template>
            </VueDraggable>
          </div>
        </div>

        <!-- 选中图片操作条：alt / 设主图 / 裁剪 / 删除 -->
        <div
          v-if="selectedIdx !== null && images[selectedIdx]"
          class="mb-4 flex flex-wrap items-center gap-2 rounded border border-blue-200 bg-blue-50 px-3 py-2 dark:border-blue-500/30 dark:bg-blue-500/10"
        >
          <span class="text-xs font-medium text-blue-600 dark:text-blue-300">已选中图片 #{{ selectedIdx + 1 }}</span>
          <NInput
            v-model:value="images[selectedIdx].alt"
            size="small"
            placeholder="alt 文本（自动保存）"
            class="!w-64"
            @update:value="onImagesDrop"
          />
          <NButton
            size="small"
            :type="images[selectedIdx].isMain ? 'success' : 'default'"
            :disabled="!!images[selectedIdx].isMain"
            @click="setMainImage(selectedIdx)"
          >
            {{ images[selectedIdx].isMain ? '主图' : '设为主图' }}
          </NButton>
          <NButton size="small" @click="openEditor(selectedIdx)">编辑图片</NButton>
          <NButton size="small" type="error" @click="removeImage(selectedIdx)">删除</NButton>
        </div>

        <NSpace size="small" align="center">
          <NUpload
            :multiple="true"
            accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml,image/bmp"
            :show-file-list="false"
            :custom-request="handleUpload"
            :disabled="uploading"
          >
            <NButton :loading="uploading">{{ $t('common.uploadImages') }}</NButton>
          </NUpload>
          <span v-if="isEdit" class="text-xs opacity-60">
            {{ imagesSaving ? '正在自动保存…' : '拖拽排序、选中操作均自动保存' }}
          </span>
        </NSpace>
      </NCard>

      <ProductImageEditor
        v-model:show="editorModal.show"
        :image-url="editorModal.show && editorModal.idx >= 0 ? images[editorModal.idx]?.url || '' : ''"
        @save="onEditorSave"
      />

      <!-- Structured detail blocks -->
      <NCard title="商品详情块（结构化）" size="small" class="md:col-span-2">
        <ProductDetailBlocks v-model:value="form.detail_blocks" />
      </NCard>

      <!-- Variants（编辑模式走独立接口，新建模式随商品创建一并上传） -->
      <NCard title="变体管理 Variants" size="small" class="md:col-span-2">
        <div class="mb-3">
          <NButton size="small" type="primary" @click="openVariantModal()">新增变体</NButton>
        </div>
        <NTable v-if="variants.length" size="small" :bordered="true" :single-line="false">
          <thead>
            <tr>
              <th>名称</th>
              <th>SKU</th>
              <th>选项 Options</th>
              <th>价格</th>
              <th>成本</th>
              <th>库存</th>
              <th>状态</th>
              <th>默认</th>
              <th style="width: 170px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in variants" :key="v.id">
              <td>{{ v.name }}</td>
              <td>{{ v.sku }}</td>
              <td class="text-xs opacity-70">{{ JSON.stringify(v.attributes || {}) }}</td>
              <td>{{ v.price }}</td>
              <td>{{ v.cost }}</td>
              <td>{{ v.inventory }}</td>
              <td>{{ v.status }}</td>
              <td>{{ v.is_default ? '✓' : '' }}</td>
              <td>
                <NSpace size="small">
                  <NButton size="tiny" @click="openVariantModal(v)">编辑</NButton>
                  <NButton size="tiny" type="error" @click="deleteVariant(v.id)">删除</NButton>
                </NSpace>
              </td>
            </tr>
          </tbody>
        </NTable>
        <NEmpty v-else description="暂无变体" size="small" class="py-6" />
      </NCard>

      <!-- Variant Modal -->
      <NModal
        v-model:show="variantModal.show"
        :title="variantModal.id ? '编辑变体' : '新增变体'"
        preset="card"
        style="width: 560px"
      >
        <NForm label-placement="top">
          <NFormItem label="SKU">
            <NInput v-model:value="variantForm.sku" placeholder="留空自动生成，如 PET-1001-BLK-M" />
          </NFormItem>
          <NFormItem label="名称" required><NInput v-model:value="variantForm.name" /></NFormItem>
          <NFormItem label="选项 Options（用于自动生成 SKU 短码）">
            <div class="w-full flex flex-col gap-1">
              <div v-if="variantForm.specRows.length" class="flex flex-col gap-1">
                <div v-for="(row, idx) in variantForm.specRows" :key="idx" class="flex items-center gap-2">
                  <NInput v-model:value="row.key" placeholder="选项名，如 Color" />
                  <NInput v-model:value="row.value" placeholder="选项值，如 Black" />
                  <NButton size="tiny" quaternary type="error" @click="removeSpecRow(idx)">删除</NButton>
                </div>
              </div>
              <div v-else class="text-xs text-gray-400">未填写选项时 SKU 仅基于货号生成</div>
              <NButton size="tiny" type="primary" quaternary style="align-self: flex-start" @click="addSpecRow">
                + 添加选项
              </NButton>
            </div>
          </NFormItem>
          <NGrid :cols="3" :x-gap="12" responsive="screen">
            <NGi>
              <NFormItem label="价格">
                <NInputNumber v-model:value="variantForm.price" :min="0" :step="0.01" style="width: 100%" />
              </NFormItem>
            </NGi>
            <NGi>
              <NFormItem label="成本">
                <NInputNumber v-model:value="variantForm.cost" :min="0" :step="0.01" style="width: 100%" />
              </NFormItem>
            </NGi>
            <NGi>
              <NFormItem label="库存">
                <NInputNumber v-model:value="variantForm.inventory" :min="0" style="width: 100%" />
              </NFormItem>
            </NGi>
          </NGrid>
          <NGrid :cols="2" :x-gap="12" responsive="screen">
            <NGi>
              <NFormItem label="状态">
                <NSelect v-model:value="variantForm.status" :options="statusOptions" />
              </NFormItem>
            </NGi>
            <NGi>
              <NFormItem label="设为默认变体"><NSwitch v-model:value="variantForm.is_default" /></NFormItem>
            </NGi>
          </NGrid>
        </NForm>
        <template #footer>
          <NSpace justify="end">
            <NButton @click="variantModal.show = false">取消</NButton>
            <NButton type="primary" :loading="variantSaving" @click="saveVariant">保存</NButton>
          </NSpace>
        </template>
      </NModal>

      <!-- SEO Score (edit only) -->
      <NCard v-if="isEdit" title="SEO 评分" size="small" class="md:col-span-2">
        <div class="grid grid-cols-1 gap-3 mb-4">
          <div>
            <div class="text-sm font-medium mb-1">SEO 标题</div>
            <NInput v-model:value="seoForm.title" placeholder="建议 30-60 字符" maxlength="200" show-count clearable />
          </div>
          <div>
            <div class="text-sm font-medium mb-1">SEO 描述</div>
            <NInput
              v-model:value="seoForm.description"
              type="textarea"
              placeholder="建议 70-160 字符"
              maxlength="300"
              show-count
              clearable
            />
          </div>
          <div>
            <div class="text-sm font-medium mb-1">SEO 关键词</div>
            <NInput v-model:value="seoForm.keywords" placeholder="逗号分隔，例如：宠物,猫粮,狗玩具" clearable />
          </div>
          <div class="flex gap-2">
            <NButton size="small" type="primary" :loading="seoSaving" @click="saveSeo">保存 SEO</NButton>
            <NButton size="small" :loading="seoLoading" @click="loadSeoScore">重新评分</NButton>
          </div>
        </div>

        <template v-if="seoScore">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <span class="text-4xl font-bold" :class="gradeColor">{{ seoScore.total_score }}</span>
              <span class="text-sm opacity-60">/ 100</span>
              <NTag v-if="seoScore.grade" size="small" :type="gradeTagType" :bordered="false">
                {{ seoScore.grade }}
              </NTag>
            </div>
          </div>

          <div v-for="d in seoScore.dimensions" :key="d.key" class="flex items-center gap-3 mb-2">
            <span class="w-24 text-sm shrink-0">{{ d.label }}</span>
            <NProgress
              class="flex-1"
              type="line"
              :percentage="maxScorePercent(d)"
              :height="8"
              :color="dimColor(d)"
              rail-color="rgba(0,0,0,0.06)"
            />
            <span class="w-14 text-right text-sm opacity-70 shrink-0">{{ d.score }}/{{ d.max }}</span>
          </div>

          <div v-if="seoScore.suggestions.length" class="mt-4">
            <div class="text-sm font-medium mb-2">优化建议</div>
            <ul class="pl-5 space-y-1">
              <li v-for="(s, i) in seoScore.suggestions" :key="i" class="text-sm opacity-80 list-disc">{{ s }}</li>
            </ul>
          </div>
          <NEmpty v-else description="SEO 状态优秀，无需优化" size="small" class="py-4" />
        </template>
        <NEmpty v-else description="点击「重新评分」获取数据" size="small" class="py-6" />
      </NCard>

      <!-- Danger Zone (edit only) -->
      <NCard v-if="isEdit" :title="$t('common.dangerZone')" size="small" class="md:col-span-2">
        <NSpace>
          <NSelect
            v-model:value="statusChange"
            :options="statusOptions"
            :placeholder="$t('page.productsDetail.changeStatus')"
            style="width: 140px"
            clearable
          />
          <NButton v-if="statusChange" type="warning" @click="changeStatus">
            {{ $t('page.productsDetail.updateStatus') }}
          </NButton>
        </NSpace>
      </NCard>
    </div>

    <div class="flex justify-end">
      <NButton type="primary" :loading="saving" @click="save">{{ $t('common.save') }}</NButton>
    </div>

    <NModal v-model:show="showAuditModal" preset="card" title="商品审核" style="width: 480px">
      <NSpace vertical>
        <NForm label-placement="top" size="small">
          <NFormItem label="审核动作">
            <NRadioGroup v-model:value="auditForm.action">
              <NRadioButton value="approve">通过</NRadioButton>
              <NRadioButton value="reject">拒绝</NRadioButton>
            </NRadioGroup>
          </NFormItem>
          <NFormItem label="审核备注 / 拒绝原因">
            <NInput
              v-model:value="auditForm.reason"
              type="textarea"
              :rows="3"
              placeholder="拒绝时必须填写原因；通过时可留备注"
            />
          </NFormItem>
        </NForm>
        <div class="text-xs text-gray-400">审核人：当前登录管理员，审核后状态与留痕不可覆盖修改。</div>
        <NSpace justify="end">
          <NButton size="small" @click="showAuditModal = false">取消</NButton>
          <NButton
            size="small"
            :type="auditForm.action === 'approve' ? 'success' : 'error'"
            @click="submitAudit"
          >
            提交审核
          </NButton>
        </NSpace>
      </NSpace>
    </NModal>
  </div>
</template>
