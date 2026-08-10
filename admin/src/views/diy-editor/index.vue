<template>
  <div class="diy-editor h-full flex flex-col gap-3">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between rounded bg-white p-3 shadow-sm dark:bg-dark">
      <div class="flex items-center gap-3">
        <NButton quaternary @click="goBack">
          <template #icon><SvgIcon icon="mdi:arrow-left" /></template>
          Back
        </NButton>
        <span class="text-base font-semibold">{{ store.currentPage?.name || '...' }}</span>
        <NTag v-if="store.currentPage" size="small" :type="store.currentPage.status === 'published' ? 'success' : 'default'">
          {{ store.currentPage.status }}
        </NTag>
        <NTag v-if="store.currentPage?.is_default" size="small" type="info">HOME</NTag>
        <NTag v-if="store.currentPage?.page_type !== 'custom'" size="small" type="warning">系统页</NTag>
      </div>
      <NSpace>
        <NButton size="small" quaternary @click="showTemplateModal = true">
          <template #icon><SvgIcon icon="mdi:file-document-multiple" /></template>
          模板
        </NButton>
        <NButton size="small" :type="showPropertyPanel ? 'primary' : 'default'" @click="showPropertyPanel = !showPropertyPanel">
          <template #icon><SvgIcon :icon="showPropertyPanel ? 'mdi:eye' : 'mdi:eye-off'" /></template>
          属性
        </NButton>
        <NButton :loading="saving" @click="save">Save Draft</NButton>
        <NButton @click="preview">Preview</NButton>
        <NButton type="primary" :loading="publishing" @click="publish">Publish</NButton>
      </NSpace>
    </div>

    <!-- 三栏布局 -->
    <div class="flex flex-1 gap-4 overflow-hidden" style="min-height: calc(100vh - 220px)">
      <ComponentPanel class="w-[280px] shrink-0" />
      <PreviewCanvas class="flex-1" />
      <PropertyPanel v-if="showPropertyPanel" class="w-[360px] shrink-0" />
    </div>

    <!-- 模板管理弹窗 -->
    <NModal v-model:show="showTemplateModal" preset="card" title="模板管理" style="width:720px">
      <NTabs v-model:value="templateTab" type="line">
        <NTabPane name="load" tab="加载模板" />
        <NTabPane name="save" tab="保存为模板" />
      </NTabs>

      <!-- 加载模板 -->
      <div v-if="templateTab === 'load'" class="mt-4">
        <div class="flex items-center gap-3 mb-3">
          <NSelect
            v-model:value="templateIndustry"
            :options="industryOptions"
            placeholder="行业筛选"
            clearable
            size="small"
            style="width:160px"
          />
          <NButton size="small" @click="fetchTemplates">刷新</NButton>
        </div>
        <NDataTable
          :columns="templateColumns"
          :data="templates"
          :loading="loadingTemplates"
          size="small"
          :bordered="false"
          max-height="320px"
        />
      </div>

      <!-- 保存为模板 -->
      <div v-if="templateTab === 'save'" class="mt-4">
        <NForm label-placement="left" label-width="90px">
          <NFormItem label="模板名称" required>
            <NInput v-model:value="saveTemplateForm.name" placeholder="如：家居装修风格" />
          </NFormItem>
          <NFormItem label="行业标签">
            <NSelect v-model:value="saveTemplateForm.industry_tag" :options="industryOptions" placeholder="可选" clearable />
          </NFormItem>
          <NFormItem label="描述">
            <NInput v-model:value="saveTemplateForm.template_description" type="textarea" :rows="2" placeholder="简要描述模板特点" />
          </NFormItem>
        </NForm>
        <NButton type="primary" block :loading="savingTemplate" @click="handleSaveAsTemplate">
          保存模板
        </NButton>
      </div>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  NPopconfirm
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { useDiyStore } from '@/store/modules/diy';
import { diyApi } from '@/service/api/diy';
import ComponentPanel from './modules/ComponentPanel.vue';
import PreviewCanvas from './modules/PreviewCanvas.vue';
import PropertyPanel from './modules/PropertyPanel.vue';

const route = useRoute();
const router = useRouter();
const store = useDiyStore();

const saving = ref(false);
const publishing = ref(false);
const showPropertyPanel = ref(false);

const pageId = route.params.id as string;

async function save() {
  saving.value = true;
  try {
    await store.saveComponents(pageId);
    window.$message?.success('Saved');
  } finally {
    saving.value = false;
  }
}

async function publish() {
  publishing.value = true;
  try {
    await store.saveComponents(pageId);
    const res = await diyApi.publishPage(pageId);
    if (store.currentPage) {
      store.currentPage.status = 'published';
    }
    window.$message?.success('Published');
  } finally {
    publishing.value = false;
  }
}

function preview() {
  const slug = store.currentPage?.slug;
  if (slug) {
    window.open(`/api/v1/diy/by-slug/${slug}?preview=true`, '_blank');
  }
}

function goBack() {
  router.push('/site/decoration');
}

// --- 模板管理 ---

const showTemplateModal = ref(false);
const templateTab = ref('load');

const templateIndustry = ref<string | null>(null);
const templates = ref<any[]>([]);
const loadingTemplates = ref(false);

const industryOptions = [
  { label: '家居', value: 'home' },
  { label: '服饰', value: 'fashion' },
  { label: '数码', value: 'electronics' },
  { label: '食品', value: 'food' },
  { label: '美妆', value: 'beauty' },
  { label: '母婴', value: 'baby' },
  { label: '运动', value: 'sports' },
  { label: '图书', value: 'books' },
  { label: '通用', value: 'general' }
];

const saveTemplateForm = reactive({
  name: '',
  industry_tag: null as string | null,
  template_description: ''
});

const savingTemplate = ref(false);

const templateColumns: DataTableColumns<any> = [
  { title: '名称', key: 'name', width: 160 },
  { title: '行业', key: 'industry_tag', width: 80 },
  { title: '描述', key: 'template_description', ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row: any) =>
      h(
        NPopconfirm,
        { onPositiveClick: () => applyTemplate(row.id) },
        {
          trigger: () => h(NButton, { size: 'tiny', type: 'primary' }, { default: () => '应用' }),
          default: () => '应用此模板将覆盖当前站点所有系统页面，确定？'
        }
      )
  }
];

async function fetchTemplates() {
  loadingTemplates.value = true;
  try {
    const params: any = { page: 1, page_size: 50 };
    if (templateIndustry.value) params.industry_tag = templateIndustry.value;
    const res = await get('/api/admin/v1/site/templates', { params });
    templates.value = res.data?.items || [];
  } finally {
    loadingTemplates.value = false;
  }
}

async function applyTemplate(id: string) {
  try {
    await post(`/api/admin/v1/site/templates/${id}/apply`);
    window.$message?.success('模板已应用，请刷新页面查看');
    showTemplateModal.value = false;
    // 重新加载当前页面数据
    await store.fetchPage(pageId);
  } catch {
    window.$message?.error('应用模板失败');
  }
}

async function handleSaveAsTemplate() {
  if (!saveTemplateForm.name) {
    window.$message?.warning('请输入模板名称');
    return;
  }
  savingTemplate.value = true;
  try {
    await post('/api/admin/v1/site/templates', saveTemplateForm);
    window.$message?.success('模板已保存');
    saveTemplateForm.name = '';
    saveTemplateForm.industry_tag = null;
    saveTemplateForm.template_description = '';
    templateTab.value = 'load';
    await fetchTemplates();
  } catch {
    window.$message?.error('保存模板失败');
  } finally {
    savingTemplate.value = false;
  }
}

import { h } from 'vue';
import { get, post } from '@/service/api/helper';

onMounted(async () => {
  store.reset();
  await Promise.all([
    store.fetchComponentsLibrary(),
    store.fetchPage(pageId),
    fetchTemplates()
  ]);
});

onUnmounted(() => {
  store.reset();
});
</script>

<style scoped>
.diy-editor {
  min-height: 100%;
}
</style>
