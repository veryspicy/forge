<script setup lang="ts">
import { ref, onMounted, computed, h } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NDataTable,
  NInput,
  NSelect,
  NSpace,
  NTag,
  NPopconfirm,
  useMessage
} from 'naive-ui';
import { get, del, post } from '@/service/api/helper';
import { contentLocaleShort, buildContentLocaleSelectOptions } from '@/constants/content-locale';
import { useDiyStore } from '@/store/modules/diy';
import type { DataTableColumns } from 'naive-ui';

const router = useRouter();
const { t } = useI18n();
const message = useMessage();

const loading = ref(false);
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const search = ref('');
const status = ref<string | null>(null);
const locale = ref<string | null>(null);

const statusOptions = [
  { label: t('page.content.draft'), value: 'draft' },
  { label: t('page.content.published'), value: 'published' }
];

// 语言下拉：运行时读站点配置（i18n 总闸 + 勾选清单），单语模式只剩默认语言
const diyStore = useDiyStore();
const localeOptions = computed(() => buildContentLocaleSelectOptions(diyStore.siteConfig.i18n));

async function fetchData() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value };
    if (search.value) params.search = search.value;
    if (status.value) params.status = status.value;
    if (locale.value) params.locale = locale.value;
    const res = await get('/api/admin/v1/content/', params);
    items.value = res.data?.items ?? [];
    total.value = res.data?.total ?? 0;
  } finally {
    loading.value = false;
  }
}

function openEdit(row?: any) {
  if (row) {
    router.push({ path: '/content/edit', query: { id: row.id } });
  } else {
    router.push('/content/edit');
  }
}

async function toggleStatus(row: any) {
  const url = `/api/admin/v1/content/${row.id}/${row.status === 'published' ? 'unpublish' : 'publish'}`;
  await post(url);
  message.success(row.status === 'published' ? t('page.content.unpublished') : t('page.content.published'));
  fetchData();
}

async function remove(row: any) {
  await del(`/api/admin/v1/content/${row.id}`);
  message.success(t('common.deleteSuccess'));
  fetchData();
}

const columns: DataTableColumns<any> = [
  { title: t('page.content.title'), key: 'title' },
  { title: 'Slug', key: 'slug' },
  {
    title: 'Lang',
    key: 'locale',
    render: row =>
      h(
        NTag,
        { type: row.locale === 'en' ? 'default' : 'info', size: 'small' },
        { default: () => contentLocaleShort(row.locale) }
      )
  },
  {
    title: t('common.status'),
    key: 'status',
    render: row =>
      h(
        NTag,
        { type: row.status === 'published' ? 'success' : 'warning', size: 'small' },
        { default: () => (row.status === 'published' ? t('page.content.published') : t('page.content.draft')) }
      )
  },
  { title: t('page.content.seoTitle'), key: 'seo_title', render: row => row.seo_title || '-' },
  {
    title: t('common.updateTime'),
    key: 'updated_at',
    render: row => (row.updated_at ? new Date(row.updated_at).toLocaleString() : '-')
  },
  {
    title: t('common.action'),
    key: 'actions',
    render: row =>
      h(
        NSpace,
        { size: 'small' },
        {
          default: () => [
            h(NButton, { size: 'small', onClick: () => openEdit(row) }, { default: () => t('common.edit') }),
            h(
              NButton,
              {
                size: 'small',
                type: row.status === 'published' ? 'default' : 'primary',
                onClick: () => toggleStatus(row)
              },
              {
                default: () =>
                  row.status === 'published' ? t('page.content.unpublish') : t('page.content.publish')
              }
            ),
            h(
              NPopconfirm,
              { onPositiveClick: () => remove(row) },
              {
                default: () => t('common.confirmDelete'),
                trigger: () =>
                  h(NButton, { size: 'small', type: 'error' }, { default: () => t('common.delete') })
              }
            )
          ]
        }
      )
  }
];

function onPageChange(p: number) {
  page.value = p;
  fetchData();
}

function onPageSizeChange(s: number) {
  pageSize.value = s;
  page.value = 1;
  fetchData();
}

onMounted(async () => {
  // 先取站点 i18n 配置，保证语言下拉与后端校验口径一致
  await diyStore.fetchSiteConfig();
  // 已选语言若因站点配置收敛而失效，清空筛选避免空列表
  if (locale.value && !localeOptions.value.some((opt: any) => opt.value === locale.value)) {
    locale.value = null;
  }
  fetchData();
});
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center gap-2">
      <NInput
        v-model:value="search"
        :placeholder="t('page.content.searchPlaceholder')"
        clearable
        class="w-56"
        @keyup.enter="page = 1; fetchData()"
      />
      <NSelect
        v-model:value="status"
        :options="statusOptions"
        clearable
        :placeholder="t('common.status')"
        class="w-32"
        @update:value="page = 1; fetchData()"
      />
      <NSelect
        v-model:value="locale"
        :options="localeOptions"
        clearable
        placeholder="Lang"
        class="w-32"
        @update:value="page = 1; fetchData()"
      />
      <NButton type="primary" @click="page = 1; fetchData()">{{ t('common.search') }}</NButton>
      <NButton type="info" @click="openEdit()">{{ t('common.add') }}</NButton>
    </div>
    <NDataTable
      :columns="columns"
      :data="items"
      :loading="loading"
      :pagination="{
        page: page,
        pageSize: pageSize,
        itemCount: total,
        onChange: onPageChange,
        onUpdatePageSize: onPageSizeChange
      }"
    />
  </div>
</template>
