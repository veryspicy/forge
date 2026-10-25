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
/** 只读预览模式：?mode=view 进入默认预览；「开始编辑」可切换解除只读（PRODUCT-VIEW-EDIT-MODE） */
const editingEnabled = ref(false);
const readonly = computed(() => route.query.mode === 'view' && !editingEnabled.value);

function startEdit() {
  editingEnabled.value = true;
}

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

// 商品审核开关（PRODUCT-AUDIT-FLOW 开关化）：关闭（默认）时隐藏审核信息卡与审核入口
const auditEnabled = ref(false);

async function loadAuditSwitch() {
  try {
    const res = await get('/api/admin/v1/settings/');
    auditEnabled.value = !!((res as any)?.data?.product_audit_enabled ?? false);
  } catch {
    auditEnabled.value = false;
  }
}

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
    action: 'approve',
    reason: ''
  };
  showAuditModal.value = true;
}

/** 只读预览：详情块内容概要文本（PRODUCT-AUDIT-FLOW 只读模式） */
function blockSummary(b: Record<string, any>): string {
  const type = String(b.type ?? '');
  const text = (v: any): string => (v == null || v === '' ? '' : String(v));
  const firstText = (arr: any[] | undefined, key: string): string =>
    Array.isArray(arr) && arr.length ? text(arr[0][key]) : '';
  switch (type) {
    case 'rich_text':
      return (
        text(b.html)
          ?.replace(/<[^>]+>/g, '')
          ?.slice(0, 120) || ''
      );
    case 'image':
      return Array.isArray(b.images) && b.images.length ? `${b.images.length} 张图片` : '';
    case 'image_text':
      return text(b.text)?.slice(0, 120) || '';
    case 'spec_table':
      return `${text(b.caption) || '规格表'}（${Array.isArray(b.rows) ? b.rows.length : 0} 行）`;
    case 'features':
      return Array.isArray(b.items) ? `${b.items.length} 个卖点` : '';
    case 'faq':
      return Array.isArray(b.items) ? `${b.items.length} 个 FAQ` : '';
    case 'video':
      return text(b.url)?.slice(0, 80) || '';
    default:
      return firstText(b.items, 'title') || text(b.caption) || '';
  }
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
const statusChange = ref<string | null>(null);

/** 详情块内上传/登记的资源 ID（由 ProductDetailBlocks 上报，保存时随 syncRefs 追踪引用） */
const detailResourceIds = ref<string[]>([]);

const images = ref<
  {
    key: string;
    url: string;
    alt?: string;
    alt_translations?: Record<string, string>;
    resourceId?: string;
    isMain?: boolean;
  }[]
>([]);
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
  name_translations: {} as Record<string, string>,
  specRows: [] as { key: string; value: string }[],
  baseAttributes: {} as Record<string, string>,
  attributes_translations: {} as Record<string, Record<string, string>>,
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
function attrsToSpecRows(
  attrs: Record<string, any> | null | undefined,
  translations?: Record<string, Record<string, string>> | null,
  lang?: string
): { key: string; value: string }[] {
  const base = attrs ?? {};
  const langMap = translations?.[lang ?? ''] ?? {};
  const rows: { key: string; value: string }[] = [];
  for (const [k, v] of Object.entries(base)) {
    // 基准语言读主列；其他语言读该语言翻译（未翻译回退基准值，作为 placeholder 参考）
    const value = lang && lang !== 'zh-cn' ? (langMap[k] ?? '') : v;
    rows.push({ key: String(k), value: value == null ? '' : String(value) });
  }
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
  name_translations: {} as Record<string, string>,
  description_translations: {} as Record<string, string>,
  /** 结构化详情块（字段受后端 DETAIL_BLOCK_FIELDS 白名单约束） */
  detail_blocks: [] as Record<string, any>[],
  /** 详情块多语言：{locale: [blocks]}，detail_blocks 为基准语言（zh-cn） */
  detail_blocks_translations: {} as Record<string, Record<string, any>[]>,
  /** SEO 多语言：{locale: {title, description, keywords[]}}，seo_* 为基准语言 */
  seo_translations: {} as Record<string, { title?: string; description?: string; keywords?: string[] }>
});

const langOptions = [
  { label: 'English (en)', value: 'en' },
  { label: 'العربية (ar)', value: 'ar' },
  { label: '简体中文 (zh-cn)', value: 'zh-cn' },
  { label: 'Français (fr)', value: 'fr' },
  { label: 'Español (es)', value: 'es' },
  { label: 'Deutsch (de)', value: 'de' }
];

/** 全局编辑语言：顶部语言标签切换；zh-cn 为基准语言（走主列），其余语言写 *_translations[lang] */
const currentLang = ref('zh-cn');

/** 变体属性按当前语言展开为键值对（基准语言走 attributes，其他语言走 translations 回退基准） */
function variantAttrs(v: any): { key: string; value: string }[] {
  const base = v.attributes || {};
  if (currentLang.value === 'zh-cn') {
    return Object.entries(base).map(([k, val]) => ({ key: k, value: String(val ?? '') }));
  }
  const map = (v.attributes_translations || {})[currentLang.value] || {};
  return Object.entries(base).map(([k, val]) => ({ key: k, value: String(map[k] ?? val ?? '') }));
}

function langStatus(lang: string): boolean {
  const seo = form.value.seo_translations?.[lang];
  return !!(
    form.value.name_translations?.[lang] ||
    form.value.description_translations?.[lang] ||
    seo?.title ||
    seo?.description ||
    seo?.keywords?.length ||
    (lang !== 'zh-cn' && !!form.value.detail_blocks_translations?.[lang]?.length)
  );
}

function switchLang(lang: string) {
  currentLang.value = lang;
}

/** 名称按当前编辑语言路由：zh-cn 走基准主列，其余语言写 name_translations[lang] */
const displayName = computed({
  get: () =>
    currentLang.value === 'zh-cn' ? form.value.name : form.value.name_translations?.[currentLang.value] || '',
  set: (v: string) => {
    if (currentLang.value === 'zh-cn') {
      form.value.name = v;
    } else {
      form.value.name_translations = { ...form.value.name_translations, [currentLang.value]: v };
    }
  }
});

/** 描述按当前编辑语言路由：zh-cn 走基准主列，其余语言写 description_translations[lang] */
const displayDesc = computed({
  get: () =>
    currentLang.value === 'zh-cn'
      ? form.value.description
      : form.value.description_translations?.[currentLang.value] || '',
  set: (v: string) => {
    if (currentLang.value === 'zh-cn') {
      form.value.description = v;
    } else {
      form.value.description_translations = { ...form.value.description_translations, [currentLang.value]: v };
    }
  }
});

/** SEO 标题按当前编辑语言路由：zh-cn 走 seoForm（基准主列），其余语言写 seo_translations[lang] */
const displaySeoTitle = computed({
  get: () =>
    currentLang.value === 'zh-cn' ? seoForm.value.title : form.value.seo_translations?.[currentLang.value]?.title || '',
  set: (v: string) => {
    if (currentLang.value === 'zh-cn') {
      seoForm.value.title = v;
    } else {
      const cur = { ...form.value.seo_translations?.[currentLang.value] };
      cur.title = v;
      form.value.seo_translations = { ...form.value.seo_translations, [currentLang.value]: cur };
    }
  }
});

/** SEO 描述按当前编辑语言路由：zh-cn 走 seoForm，其余语言写 seo_translations[lang] */
const displaySeoDesc = computed({
  get: () =>
    currentLang.value === 'zh-cn'
      ? seoForm.value.description
      : form.value.seo_translations?.[currentLang.value]?.description || '',
  set: (v: string) => {
    if (currentLang.value === 'zh-cn') {
      seoForm.value.description = v;
    } else {
      const cur = { ...form.value.seo_translations?.[currentLang.value] };
      cur.description = v;
      form.value.seo_translations = { ...form.value.seo_translations, [currentLang.value]: cur };
    }
  }
});

/** SEO 关键词按当前编辑语言路由：zh-cn 走 seoForm，其余语言写 seo_translations[lang] */
const displaySeoKeywords = computed({
  get: () =>
    currentLang.value === 'zh-cn'
      ? seoForm.value.keywords
      : (form.value.seo_translations?.[currentLang.value]?.keywords || []).join(', '),
  set: (v: string) => {
    const keywords = v
      .split(',')
      .map((k: string) => k.trim())
      .filter(Boolean);
    if (currentLang.value === 'zh-cn') {
      seoForm.value.keywords = v;
    } else {
      const cur = { ...form.value.seo_translations?.[currentLang.value] };
      cur.keywords = keywords;
      form.value.seo_translations = { ...form.value.seo_translations, [currentLang.value]: cur };
    }
  }
});

/** 变体名称按当前编辑语言路由：zh-cn 走 name 主列，其余语言写 name_translations[lang] */
const variantDisplayName = computed({
  get: () =>
    currentLang.value === 'zh-cn'
      ? variantForm.value.name
      : variantForm.value.name_translations?.[currentLang.value] || '',
  set: (v: string) => {
    if (currentLang.value === 'zh-cn') {
      variantForm.value.name = v;
    } else {
      variantForm.value.name_translations = { ...variantForm.value.name_translations, [currentLang.value]: v };
    }
  }
});

/** 变体表格展示：当前语言名，缺失回退基准名 */
function variantDisplayNameOf(v: any): string {
  return currentLang.value === 'zh-cn' ? v.name || '' : v.name_translations?.[currentLang.value] || v.name || '';
}

/** 当前语言下可见的详情块：zh-cn 走基准块，其余语言走该语言的整组翻译块（缺失回退空数组，编辑即写入） */
const activeBlocks = computed<Record<string, any>[]>({
  get: () =>
    currentLang.value === 'zh-cn'
      ? form.value.detail_blocks || []
      : form.value.detail_blocks_translations?.[currentLang.value] || [],
  set: v => {
    if (currentLang.value === 'zh-cn') {
      form.value.detail_blocks = v;
    } else {
      form.value.detail_blocks_translations[currentLang.value] = v;
    }
  }
});

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

onMounted(async () => {
  loadAuditSwitch();
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
      name_translations: p.name_translations || {},
      description_translations: p.description_translations || {},
      detail_blocks: (p.detail_blocks || []) as Record<string, any>[],
      detail_blocks_translations: (p.detail_blocks_translations || {}) as Record<string, Record<string, any>[]>,
      seo_translations: (p.seo_translations || {}) as Record<
        string,
        { title?: string; description?: string; keywords?: string[] }
      >
    };
    tagsString.value = (p.tags || []).join(', ');
    images.value = (p.images || [])
      .slice()
      .sort((a: any, b: any) => Number(a.sort ?? 0) - Number(b.sort ?? 0))
      .map((i: any) => ({
        key: i.key || '',
        url: i.url || '',
        alt: i.alt || '',
        alt_translations: i.alt_translations || {},
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
          alt_translations: uploaded.alt_translations || {},
          resourceId: uploaded.resource_id || ''
        });
    } catch (e: any) {
      error.value = e.response?.data?.detail || t('common.uploadFailed') + ': ' + file.name;
    }
  } else {
    pendingFiles.value.push(file);
    images.value.push({ key: '', url: URL.createObjectURL(file), alt: '', alt_translations: {} });
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

/** 当前语言下图片 alt 展示值：zh-cn 读基准 alt，其余语种读 alt_translations */
function imageAlt(img: any) {
  if (currentLang.value !== 'zh-cn') {
    return img.alt_translations?.[currentLang.value] || '';
  }
  return img.alt || '';
}

/** 按当前语言写入图片 alt：zh-cn 写基准 alt，其余语种写 alt_translations[lang] */
function setImageAlt(idx: number, value: string) {
  const img = images.value[idx];
  if (!img) return;
  if (currentLang.value === 'zh-cn') {
    img.alt = value;
  } else {
    if (!img.alt_translations) img.alt_translations = {};
    img.alt_translations[currentLang.value] = value;
  }
  onImagesDrop();
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
      alt_translations: uploaded.alt_translations || images.value[idx].alt_translations || {},
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
      alt_translations: img.alt_translations || {},
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
          alt_translations: i.alt_translations || {},
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
  try {
    const payload = buildPayload();
    // 基准语言 SEO 随主表单一并提交（编辑模式下与「保存 SEO」幂等）
    payload.seo_title = seoForm.value.title;
    payload.seo_description = seoForm.value.description;
    payload.seo_keywords = seoForm.value.keywords
      .split(',')
      .map((k: string) => k.trim())
      .filter(Boolean);
    if (isEdit.value) {
      await patch(`/api/admin/v1/products/${route.params.id}`, payload);
      await syncProductRefs(String(route.params.id));
    } else {
      // 新建商品时一并上传本地变体（后端 ProductCreate.variants 批量创建）
      payload.variants = variants.value.map(v => ({
        sku: v.sku || '',
        name: v.name || '',
        attributes: v.attributes || {},
        attributes_translations: v.attributes_translations || {},
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
            alt_translations: uploaded.alt_translations || {},
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
  const resourceIds = [
    ...images.value.map(i => i.resourceId).filter(Boolean),
    ...detailResourceIds.value
  ] as string[];
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
      name_translations: (v.name_translations || {}) as Record<string, string>,
      specRows: attrsToSpecRows(
        v.attributes ??
          (v.specs ? Object.fromEntries((v.specs as any[]).map((s: any) => [s.spec_key, s.value])) : null),
        (v.attributes_translations || {}) as Record<string, Record<string, string>>,
        currentLang.value
      ),
      baseAttributes: (v.attributes || {}) as Record<string, string>,
      attributes_translations: (v.attributes_translations || {}) as Record<string, Record<string, string>>,
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
      name_translations: {},
      specRows: [],
      baseAttributes: {},
      attributes_translations: {},
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
  const attributes: Record<string, string> = {};
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
    name_translations: variantForm.value.name_translations,
    price: variantForm.value.price,
    cost: variantForm.value.cost,
    inventory: variantForm.value.inventory,
    status: variantForm.value.status,
    is_default: variantForm.value.is_default
  };
  if (currentLang.value === 'zh-cn') {
    // 基准语言：写 attributes 主列，各语言翻译仅保留与最新基准键匹配的项（键变更时清理悬空翻译）
    payload.attributes = attributes;
    const merged: Record<string, Record<string, string>> = {};
    for (const [lang, map] of Object.entries(variantForm.value.attributes_translations)) {
      const keep: Record<string, string> = {};
      for (const k of Object.keys(attributes)) if (map[k] !== undefined) keep[k] = map[k];
      if (Object.keys(keep).length) merged[lang] = keep;
    }
    payload.attributes_translations = merged;
  } else {
    // 其他语言：基准 attributes 不可变，仅覆盖当前语言属性值翻译
    payload.attributes = variantForm.value.baseAttributes;
    payload.attributes_translations = {
      ...variantForm.value.attributes_translations,
      [currentLang.value]: attributes
    };
  }
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
        {{
          isEdit
            ? (readonly ? t('common.view') : t('common.edit')) + ' ' + t('common.product')
            : t('common.new') + ' ' + t('common.product')
        }}
      </h2>
      <div class="flex items-center gap-2">
        <NButton v-if="readonly" type="primary" @click="startEdit">开始编辑</NButton>
        <NButton @click="$router.push('/products')">{{ $t('common.backToList') }}</NButton>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 text-red-600 p-3 rounded text-sm">{{ error }}</div>

    <!-- 全局编辑语言：所有多语言字段按当前语言联动；zh-cn 为基准语言，其余语言写入对应 translations -->
    <NCard size="small" class="md:col-span-2">
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-sm font-medium">编辑语言</span>
        <div class="flex flex-wrap gap-2">
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
            :title="opt.value"
            @click="switchLang(opt.value)"
          >
            {{ opt.label }}
            <span :class="langStatus(opt.value) ? 'text-green-400' : 'text-amber-400'">●</span>
          </button>
        </div>
        <span class="text-xs text-gray-400">
          当前编辑语言由上方标签标明；● 绿=已填写，黄=未翻译（C 端自动回退基准语言 zh-cn）
        </span>
      </div>
    </NCard>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Basic Info -->
      <NCard :title="$t('common.basicInfo')" size="small" class="md:col-span-2">
        <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.sku')" required>
              <NInput v-model:value="form.sku" :disabled="readonly" />
            </NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.name')" required>
              <NInput
                v-model:value="displayName"
                :disabled="readonly"
                :placeholder="currentLang !== 'zh-cn' ? `基准：${form.name || '（空）'}` : ''"
              />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.productsDetail.slug')">
              <NInput v-model:value="form.slug" :disabled="readonly" />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.products.category')">
              <NSelect v-model:value="form.category" :options="categoryOptions" :disabled="readonly" />
            </NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem label="履约模式">
              <NSelect v-model:value="form.fulfillment_mode" :options="fulfillmentOptions" :disabled="readonly" />
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
                :disabled="readonly"
              />
            </NFormItem>
          </NGi>
          <NGi v-if="form.fulfillment_mode === 'dropship'" span="1">
            <NFormItem label="供应商 SKU">
              <NInput v-model:value="form.supplier_sku" placeholder="供应商侧货号（可选）" :disabled="readonly" />
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
                :disabled="readonly"
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
                :disabled="readonly"
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
                :disabled="readonly"
              />
            </NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.description')">
              <NInput
                v-model:value="displayDesc"
                type="textarea"
                :rows="3"
                :disabled="readonly"
                :placeholder="currentLang !== 'zh-cn' ? `基准：${form.description || '（空）'}` : ''"
              />
            </NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Product Audit（PRODUCT-AUDIT-FLOW 开关化：关闭时整卡隐藏） -->
      <NCard v-if="auditEnabled" title="商品审核" size="small" class="md:col-span-2">
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
              <span class="mr-1">审核备注:</span>
              {{ auditInfo.audit_reason }}
            </div>
          </div>
          <NButton
            v-if="isEdit && auditInfo.audit_status === 'pending' && !readonly"
            size="small"
            type="primary"
            secondary
            @click="openAuditModal"
          >
            审核
          </NButton>
        </div>
      </NCard>

      <!-- Pricing -->
      <NCard :title="$t('page.pricing.title')" size="small">
        <NFormItem :label="$t('page.products.price')">
          <NInputNumber v-model:value="form.price" :min="0" :step="0.01" style="width: 100%" :disabled="readonly" />
        </NFormItem>
        <NFormItem :label="$t('common.cost')">
          <NInputNumber v-model:value="form.cost" :min="0" :step="0.01" style="width: 100%" :disabled="readonly" />
        </NFormItem>
      </NCard>

      <!-- Inventory -->
      <NCard :title="$t('common.inventory')" size="small">
        <NFormItem :label="$t('page.productsDetail.inventory')">
          <NInputNumber v-model:value="form.inventory" :min="0" style="width: 100%" :disabled="readonly" />
        </NFormItem>
        <NFormItem :label="$t('page.productsDetail.aiGenerated')">
          <NSwitch v-model:value="form.is_ai_generated" :disabled="readonly" />
        </NFormItem>
      </NCard>

      <!-- Tags -->
      <NCard title="标签" size="small" class="md:col-span-2">
        <NFormItem :label="$t('page.productsDetail.tagsComma')">
          <NInput v-model:value="tagsString" :disabled="readonly" @update:value="updateTags" />
        </NFormItem>
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
              :disabled="readonly"
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
                      v-if="!readonly"
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
                    {{ imageAlt(img) || '无 alt' }}
                  </div>
                </div>
              </template>
            </VueDraggable>
          </div>
        </div>

        <!-- 选中图片操作条：alt / 设主图 / 裁剪 / 删除 -->
        <div
          v-if="!readonly && selectedIdx !== null && images[selectedIdx]"
          class="mb-4 flex flex-wrap items-center gap-2 rounded border border-blue-200 bg-blue-50 px-3 py-2 dark:border-blue-500/30 dark:bg-blue-500/10"
        >
          <span class="text-xs font-medium text-blue-600 dark:text-blue-300">已选中图片 #{{ selectedIdx + 1 }}</span>
          <NInput
            :value="imageAlt(images[selectedIdx])"
            size="small"
            placeholder="alt 文本（当前语言，自动保存）"
            class="!w-64"
            @update:value="setImageAlt(selectedIdx, $event)"
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
            :disabled="uploading || readonly"
          >
            <NButton v-if="!readonly" :loading="uploading">{{ $t('common.uploadImages') }}</NButton>
          </NUpload>
          <span v-if="isEdit && !readonly" class="text-xs opacity-60">
            {{ imagesSaving ? '正在自动保存…' : '拖拽排序、选中操作均自动保存' }}
          </span>
        </NSpace>
      </NCard>

      <ProductImageEditor
        v-model:show="editorModal.show"
        :image-url="editorModal.show && editorModal.idx >= 0 ? images[editorModal.idx]?.url || '' : ''"
        @save="onEditorSave"
      />

      <!-- Structured detail blocks（当前编辑语言下编辑；zh-cn 为基准块，其他语言写入 detail_blocks_translations） -->
      <NCard title="商品详情块（结构化）" size="small" class="md:col-span-2">
        <template v-if="readonly">
          <div v-if="!activeBlocks.length" class="text-xs opacity-60">无详情块</div>
          <div
            v-for="(b, i) in activeBlocks"
            :key="i"
            class="mb-2 rounded border border-[var(--n-border-color)] px-3 py-2"
          >
            <div class="flex items-center gap-2">
              <NTag size="small">{{ String(b.type ?? 'block') }}</NTag>
              <span class="text-sm font-medium">{{ String(b.title ?? '') }}</span>
            </div>
            <div class="mt-1 text-xs opacity-70">{{ blockSummary(b) || '（无内容）' }}</div>
          </div>
        </template>
        <template v-else>
          <ProductDetailBlocks v-model:value="activeBlocks" @resources="(ids: string[]) => (detailResourceIds = ids)" />
          <div v-if="currentLang !== 'zh-cn'" class="mt-2 text-xs opacity-60">
            当前编辑语言块（C 端按语言整组回退基准语言）
          </div>
        </template>
      </NCard>

      <!-- Variants（编辑模式走独立接口，新建模式随商品创建一并上传） -->
      <NCard title="变体管理 Variants" size="small" class="md:col-span-2">
        <div class="mb-3">
          <NButton v-if="!readonly" size="small" type="primary" @click="openVariantModal()">新增变体</NButton>
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
              <td>{{ variantDisplayNameOf(v) }}</td>
              <td>{{ v.sku }}</td>
              <td>
                <NSpace v-if="variantAttrs(v).length" size="small" :wrap="true">
                  <NTag v-for="a in variantAttrs(v)" :key="a.key" size="small" :bordered="false">
                    {{ a.key }}: {{ a.value }}
                  </NTag>
                </NSpace>
                <span v-else class="text-xs opacity-50">-</span>
              </td>
              <td>{{ v.price }}</td>
              <td>{{ v.cost }}</td>
              <td>{{ v.inventory }}</td>
              <td>{{ v.status }}</td>
              <td>{{ v.is_default ? '✓' : '' }}</td>
              <td>
                <NSpace size="small">
                  <template v-if="!readonly">
                    <NButton size="tiny" @click="openVariantModal(v)">编辑</NButton>
                    <NButton size="tiny" type="error" @click="deleteVariant(v.id)">删除</NButton>
                  </template>
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
          <NFormItem label="名称" required>
            <NInput
              v-model:value="variantDisplayName"
              :placeholder="currentLang !== 'zh-cn' ? `基准：${variantForm.name || '（空）'}` : '该语言下的展示名'"
            />
          </NFormItem>
          <NFormItem label="选项 Options（用于自动生成 SKU 短码）">
            <div class="w-full flex flex-col gap-1">
              <div v-if="variantForm.specRows.length" class="flex flex-col gap-1">
                <div v-for="(row, idx) in variantForm.specRows" :key="idx" class="flex items-center gap-2">
                  <NInput v-model:value="row.key" placeholder="选项名，如 Color" :disabled="currentLang !== 'zh-cn'" />
                  <NInput
                    v-model:value="row.value"
                    :placeholder="
                      currentLang !== 'zh-cn'
                        ? `基准：${variantForm.baseAttributes[row.key] ?? '（空）'}`
                        : '选项值，如 Black'
                    "
                  />
                  <NButton
                    v-if="currentLang === 'zh-cn'"
                    size="tiny"
                    quaternary
                    type="error"
                    @click="removeSpecRow(idx)"
                  >
                    删除
                  </NButton>
                  <span v-else class="text-xs text-gray-400">基准键</span>
                </div>
              </div>
              <div v-else class="text-xs text-gray-400">未填写选项时 SKU 仅基于货号生成</div>
              <NButton
                v-if="currentLang === 'zh-cn'"
                size="tiny"
                type="primary"
                quaternary
                style="align-self: flex-start"
                @click="addSpecRow"
              >
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

      <!-- SEO（按当前编辑语言联动：zh-cn 走基准主列并支持评分，其余语言写 seo_translations[lang]） -->
      <NCard title="SEO" size="small" class="md:col-span-2">
        <div class="grid grid-cols-1 gap-3 mb-4">
          <div>
            <div class="text-sm font-medium mb-1">SEO 标题</div>
            <NInput
              v-model:value="displaySeoTitle"
              placeholder="建议 30-60 字符"
              maxlength="200"
              show-count
              clearable
              :disabled="readonly"
            />
          </div>
          <div>
            <div class="text-sm font-medium mb-1">SEO 描述</div>
            <NInput
              v-model:value="displaySeoDesc"
              type="textarea"
              placeholder="建议 70-160 字符"
              maxlength="300"
              show-count
              clearable
              :disabled="readonly"
            />
          </div>
          <div>
            <div class="text-sm font-medium mb-1">SEO 关键词</div>
            <NInput
              v-model:value="displaySeoKeywords"
              placeholder="逗号分隔，例如：宠物,猫粮,狗玩具"
              clearable
              :disabled="readonly"
            />
          </div>
          <div class="flex gap-2 items-center">
            <template v-if="currentLang === 'zh-cn' && isEdit && !readonly">
              <NButton size="small" type="primary" :loading="seoSaving" @click="saveSeo">保存 SEO</NButton>
              <NButton size="small" :loading="seoLoading" @click="loadSeoScore">重新评分</NButton>
            </template>
            <span v-else-if="currentLang !== 'zh-cn'" class="text-xs opacity-60">
              当前语言 SEO 随主表单「保存」一并提交；留空则 C 端回退基准语言
            </span>
            <span v-else class="text-xs opacity-60">保存商品时随主表单提交</span>
          </div>
        </div>

        <template v-if="isEdit && currentLang === 'zh-cn' && seoScore">
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
        <NEmpty
          v-else-if="isEdit && currentLang === 'zh-cn'"
          description="点击「重新评分」获取数据"
          size="small"
          class="py-6"
        />
      </NCard>

      <!-- Danger Zone (edit only) -->
      <NCard v-if="isEdit && !readonly" :title="$t('common.dangerZone')" size="small" class="md:col-span-2">
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
      <NButton v-if="!readonly" type="primary" :loading="saving" @click="save">{{ $t('common.save') }}</NButton>
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
          <NButton size="small" :type="auditForm.action === 'approve' ? 'success' : 'error'" @click="submitAudit">
            提交审核
          </NButton>
        </NSpace>
      </NSpace>
    </NModal>
  </div>
</template>
