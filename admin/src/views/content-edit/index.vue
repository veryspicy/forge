<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
  NForm,
  NFormItem,
  NInput,
  NButton,
  NSelect,
  NSpace,
  NPopconfirm,
  useMessage
} from 'naive-ui';
import { get, post, patch, del } from '@/service/api/helper';
import { buildContentLocaleSelectOptions, resolveActiveLocales } from '@/constants/content-locale';
import { useDiyStore } from '@/store/modules/diy';
import { CONTENT_TEMPLATES, getTemplateBody } from '@/constants/content-templates';
import RichTextEditor from '@/components/RichTextEditor.vue';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const message = useMessage();

const id = route.query.id as string | undefined;
const loading = ref(false);
const saving = ref(false);

const form = ref({
  slug: '',
  locale: 'en',
  title: '',
  body: '',
  seo_title: '',
  seo_description: '',
  status: 'draft'
});

const statusOptions = [
  { label: t('page.content.draft'), value: 'draft' },
  { label: t('page.content.published'), value: 'published' }
];

// 语言下拉：运行时读站点配置（i18n 总闸 + 勾选清单）；存量内容所在语言始终允许保留
const diyStore = useDiyStore();
const localeOptions = computed(() => {
  const options = buildContentLocaleSelectOptions(diyStore.siteConfig.i18n);
  const current = form.value.locale;
  if (current && !options.some(opt => opt.value === current)) {
    options.unshift({ label: current.toUpperCase(), value: current });
  }
  return options;
});

// 富文本编辑器开关：inline 模式展开在表单内，保存后回写 form.body（HTML）
const editorShow = ref(false);

// 内容骨架模板：一键插入结构化 HTML（隐私政策 / 服务条款 / 配送政策 / FAQ）
const templateOptions = CONTENT_TEMPLATES.map(item => ({ label: item.label, value: item.key }));
const selectedTemplate = ref<string | null>(null);

function insertTemplate() {
  const tpl = CONTENT_TEMPLATES.find(item => item.key === selectedTemplate.value);
  if (!tpl) {
    message.warning('请先选择内容模板');
    return;
  }
  const html = getTemplateBody(tpl, form.value.locale);
  if (!html) {
    message.warning('该模板暂无内容');
    return;
  }
  const isFallback = form.value.locale !== 'en' && form.value.locale !== 'zh';
  if (!form.value.body.trim()) {
    form.value.body = html;
  } else {
    form.value.body = `${form.value.body.trimEnd()}\n\n${html}`;
  }
  message.success(
    isFallback
      ? `已插入 ${tpl.label}（${form.value.locale} 暂无骨架，已用 en 版本，请翻译后发布）`
      : `已插入模板：${tpl.label}`
  );
}

function applyBody(html: string) {
  form.value.body = html;
}

async function load() {
  if (!id) return;
  loading.value = true;
  try {
    const res = await get(`/api/admin/v1/content/${id}`);
    // 兼容后端详情接口 {data:{...}} 包裹与无包裹两种响应
    const d = res.data?.data ?? res.data;
    form.value = {
      slug: d.slug ?? '',
      locale: d.locale ?? 'en',
      title: d.title ?? '',
      body: d.body ?? '',
      seo_title: d.seo_title ?? '',
      seo_description: d.seo_description ?? '',
      status: d.status ?? 'draft'
    };
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    if (id) {
      await patch(`/api/admin/v1/content/${id}`, form.value);
      message.success(t('common.saveSuccess'));
    } else {
      await post('/api/admin/v1/content/', form.value);
      message.success(t('common.addSuccess'));
    }
    router.back();
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!id) return;
  await del(`/api/admin/v1/content/${id}`);
  message.success(t('common.deleteSuccess'));
  router.push('/content');
}

// 预览栏宽度：拖拽分隔条调整，范围 260px ~ 视口 60%，宽度持久化到 localStorage
const PREVIEW_MIN_WIDTH = 260;
const PREVIEW_DEFAULT_WIDTH = 360;
const PREVIEW_MAX_RATIO = 0.6;
const PREVIEW_STORAGE_KEY = 'forge:content-preview-width';

const previewWidth = ref(PREVIEW_DEFAULT_WIDTH);
const resizing = ref(false);

function clampPreviewWidth(value: number) {
  const max = Math.max(PREVIEW_MIN_WIDTH, Math.floor(window.innerWidth * PREVIEW_MAX_RATIO));
  return Math.min(Math.max(Math.round(value), PREVIEW_MIN_WIDTH), max);
}

function loadPreviewWidth() {
  const saved = Number(localStorage.getItem(PREVIEW_STORAGE_KEY));
  previewWidth.value = Number.isFinite(saved) && saved > 0 ? clampPreviewWidth(saved) : PREVIEW_DEFAULT_WIDTH;
}

function persistPreviewWidth(width: number) {
  localStorage.setItem(PREVIEW_STORAGE_KEY, String(width));
}

function resetPreviewWidth() {
  previewWidth.value = PREVIEW_DEFAULT_WIDTH;
  persistPreviewWidth(PREVIEW_DEFAULT_WIDTH);
}

// 分隔条在预览左侧：鼠标左移 => 预览变宽
function startResize(event: MouseEvent) {
  if (event.button !== 0 || resizing.value) return;
  event.preventDefault();
  resizing.value = true;
  const startX = event.clientX;
  const startWidth = previewWidth.value;
  const onMove = (ev: MouseEvent) => {
    previewWidth.value = clampPreviewWidth(startWidth + (startX - ev.clientX));
  };
  const onUp = () => {
    resizing.value = false;
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
    document.body.style.removeProperty('user-select');
    persistPreviewWidth(previewWidth.value);
  };
  // 拖拽期间禁用文本选中，避免划选正文
  document.body.style.userSelect = 'none';
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
}

// 窗口收窄时收缩到合法区间，避免预览挤掉正文
function handleWindowResize() {
  previewWidth.value = clampPreviewWidth(previewWidth.value);
}

onMounted(async () => {
  loadPreviewWidth();
  window.addEventListener('resize', handleWindowResize);
  // 先取站点 i18n 配置：新建内容默认落到站点默认语言，下拉与后端校验同源
  await diyStore.fetchSiteConfig();
  if (!id) {
    form.value.locale = resolveActiveLocales(diyStore.siteConfig.i18n)[0] || 'en';
  }
  await load();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize);
});
</script>

<template>
  <div class="content-edit-layout p-4" :style="{ '--preview-w': `${previewWidth}px` }">
    <NForm label-placement="left" label-width="120" :show-require-mark="false" class="w-full min-w-0">
      <NFormItem label="Slug" :required="true">
        <NInput v-model:value="form.slug" placeholder="faqs / shipping / privacy" :disabled="loading" />
      </NFormItem>
      <NFormItem label="Lang" :required="true">
        <NSelect v-model:value="form.locale" :options="localeOptions" :disabled="loading" class="w-40" />
      </NFormItem>
      <NFormItem :label="t('page.content.title')" :required="true">
        <NInput v-model:value="form.title" :disabled="loading" />
      </NFormItem>
      <NFormItem :label="t('page.content.body')">
        <div class="w-full flex flex-col gap-2">
          <div class="flex items-center justify-between gap-3">
            <span class="text-xs text-gray-500">
              HTML 正文，C 端按统一富文本基线排版（标题 / 列表 / 引用 / 图片 / 视频）
            </span>
            <div class="flex items-center gap-2">
              <NSelect
                v-model:value="selectedTemplate"
                :options="templateOptions"
                size="small"
                placeholder="内容骨架模板"
                clearable
                class="w-52"
              />
              <NButton size="small" :disabled="loading" @click="insertTemplate">插入模板</NButton>
              <NButton size="small" :disabled="loading" @click="editorShow = !editorShow">
                {{ editorShow ? '收起编辑器' : '富文本编辑' }}
              </NButton>
            </div>
          </div>
          <!-- 复用商品详情同一套 Tiptap 编辑器（富文本 / Markdown 双模，落库 HTML） -->
          <RichTextEditor
            v-if="editorShow"
            inline
            :show="editorShow"
            :html="form.body"
            title="正文"
            @save="applyBody"
            @update:show="(v: boolean) => (editorShow = v)"
          />
          <NInput
            v-model:value="form.body"
            type="textarea"
            :rows="editorShow ? 4 : 12"
            :disabled="loading"
            placeholder="HTML content"
          />
        </div>
      </NFormItem>
      <NFormItem :label="t('page.content.seoTitle')">
        <NInput v-model:value="form.seo_title" :disabled="loading" />
      </NFormItem>
      <NFormItem :label="t('page.content.seoDescription')">
        <NInput v-model:value="form.seo_description" type="textarea" :rows="3" :disabled="loading" />
      </NFormItem>
      <NFormItem :label="t('common.status')">
        <NSelect v-model:value="form.status" :options="statusOptions" :disabled="loading" class="w-40" />
      </NFormItem>
      <NFormItem>
        <NSpace>
          <NButton type="primary" :loading="saving" @click="save">{{ t('common.save') }}</NButton>
          <NButton @click="router.back()">{{ t('common.cancel') }}</NButton>
          <NPopconfirm v-if="id" @positive-click="remove">
            <template #trigger>
              <NButton type="error">{{ t('common.delete') }}</NButton>
            </template>
            {{ t('common.confirmDelete') }}
          </NPopconfirm>
        </NSpace>
      </NFormItem>
    </NForm>

    <!-- 拖拽分隔条：调整右侧预览宽度，双击复位 -->
    <div
      class="preview-resizer"
      :class="{ 'is-active': resizing }"
      title="拖动调整预览宽度（双击复位）"
      @mousedown="startResize"
      @dblclick="resetPreviewWidth"
    />

    <aside
      class="preview-pane sticky top-4 flex max-h-[calc(100vh-2rem)] min-w-0 flex-col overflow-hidden rounded-md border border-gray-200 bg-white"
    >
      <div class="border-b border-gray-100 px-4 py-2 text-xs text-gray-400">排版预览（与前台 prose 基线近似）</div>
      <div v-if="form.body" class="rich-preview flex-1 overflow-y-auto p-4" v-html="form.body" />
      <div v-else class="flex-1 px-4 py-10 text-center text-xs text-gray-300">暂无正文，预览为空</div>
    </aside>
  </div>
</template>

<style scoped>
.content-edit-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: 1rem;
}

.preview-resizer {
  display: none;
}

@media (min-width: 1280px) {
  .content-edit-layout {
    grid-template-columns: minmax(0, 1fr) 10px var(--preview-w, 360px);
  }

  .preview-resizer {
    display: block;
    align-self: stretch;
    min-height: 120px;
    border-radius: 9999px;
    background-color: transparent;
    cursor: col-resize;
    transition: background-color 0.15s ease;
  }

  .preview-resizer:hover,
  .preview-resizer.is-active {
    background-color: #e5e7eb;
  }
}
</style>
