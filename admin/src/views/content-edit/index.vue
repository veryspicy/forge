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

const localeOptions = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh' }
];

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
  <div class="p-4">
    <NForm label-placement="left" label-width="120" :show-require-mark="false" class="max-w-3xl">
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
        <NInput
          v-model:value="form.body"
          type="textarea"
          :rows="12"
          :disabled="loading"
          placeholder="HTML content"
        />
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
  </div>
</template>
