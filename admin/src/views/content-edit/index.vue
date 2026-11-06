<script setup lang="ts">
import { ref, onMounted } from 'vue';
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
import { contentLocaleOptions } from '@/constants/content-locale';
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

const localeOptions = contentLocaleOptions.map(({ label, value }) => ({ label, value }));

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

onMounted(load);
</script>

<template>
  <div class="p-4 grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(300px,1fr)]">
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

    <aside
      class="sticky top-4 flex max-h-[calc(100vh-2rem)] min-w-0 flex-col overflow-hidden rounded-md border border-gray-200 bg-white"
    >
      <div class="border-b border-gray-100 px-4 py-2 text-xs text-gray-400">排版预览（与前台 prose 基线近似）</div>
      <div v-if="form.body" class="rich-preview flex-1 overflow-y-auto p-4" v-html="form.body" />
      <div v-else class="flex-1 px-4 py-10 text-center text-xs text-gray-300">暂无正文，预览为空</div>
    </aside>
  </div>
</template>
