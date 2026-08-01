<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <NSpace>
        <NInput v-model:value="search" placeholder="Search name / slug" style="width:220px" @keyup.enter="fetch" />
        <NSelect v-model:value="status" :options="statusOptions" placeholder="Status" clearable style="width:140px" @update:value="fetch" />
        <NSelect v-model:value="pageType" :options="typeOptions" placeholder="Type" clearable style="width:160px" @update:value="fetch" />
      </NSpace>
      <NButton type="primary" @click="showCreate = true">{{ $t('common.add') }}</NButton>
    </div>

    <NDataTable :columns="columns" :data="pages" :loading="loading" :bordered="false" size="small" />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>

    <!-- 新建页面弹窗 -->
    <NModal v-model:show="showCreate" preset="card" title="New DIY Page" style="width:480px">
      <NForm label-placement="left" label-width="90px">
        <NFormItem label="Name" required>
          <NInput v-model:value="createForm.name" placeholder="e.g. Home V2" />
        </NFormItem>
        <NFormItem label="Slug" required>
          <NInput v-model:value="createForm.slug" placeholder="e.g. home_v2" />
        </NFormItem>
        <NFormItem label="Type">
          <NSelect v-model:value="createForm.page_type" :options="typeOptions" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreate = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="creating" @click="handleCreate">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NPopconfirm,
  NPagination,
  NSelect,
  NSpace,
  NTag
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { diyApi } from '@/service/api/diy';

const router = useRouter();
const loading = ref(false);
const search = ref('');
const status = ref<string | null>(null);
const pageType = ref<string | null>(null);
const pages = ref<any[]>([]);
const page = ref(1);
const total = ref(0);
const pageSize = 20;

const showCreate = ref(false);
const creating = ref(false);
const createForm = reactive({ name: '', slug: '', page_type: 'custom' });

const statusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Published', value: 'published' }
];

const typeOptions = [
  { label: 'Home', value: 'home' },
  { label: 'Category', value: 'category' },
  { label: 'Product Detail', value: 'product_detail' },
  { label: 'Custom', value: 'custom' }
];

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (status.value) params.status = status.value;
    if (pageType.value) params.page_type = pageType.value;
    const res = await diyApi.listPages(params);
    let items: any[] = res.data?.items || [];
    if (search.value) {
      const kw = search.value.toLowerCase();
      items = items.filter((p: any) => p.name?.toLowerCase().includes(kw) || p.slug?.toLowerCase().includes(kw));
    }
    pages.value = items;
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

function goPage(p: number) {
  page.value = p;
  fetch();
}

async function handleCreate() {
  if (!createForm.name || !createForm.slug) {
    window.$message?.warning('Name and Slug are required');
    return;
  }
  creating.value = true;
  try {
    const res = await diyApi.createPage({ ...createForm });
    showCreate.value = false;
    window.$message?.success('Created');
    router.push(`/site/decoration/editor/${res.data.id}`);
  } finally {
    creating.value = false;
  }
}

async function togglePublish(row: any) {
  if (row.status === 'published') {
    await diyApi.unpublishPage(row.id);
    window.$message?.success('Unpublished');
  } else {
    await diyApi.publishPage(row.id);
    window.$message?.success('Published');
  }
  fetch();
}

async function duplicate(row: any) {
  await diyApi.duplicatePage(row.id);
  window.$message?.success('Duplicated');
  fetch();
}

async function setDefault(row: any) {
  await diyApi.setDefault(row.id);
  window.$message?.success('Set as homepage');
  fetch();
}

async function remove(row: any) {
  await diyApi.deletePage(row.id);
  window.$message?.success('Deleted');
  fetch();
}

function preview(row: any) {
  window.open(`/api/v1/diy/pages/${row.slug}?preview=true`, '_blank');
}

const columns: DataTableColumns<any> = [
  { title: 'Name', key: 'name', render: row => h('span', {}, [row.name, row.is_default ? h(NTag, { size: 'tiny', type: 'success', style: { marginLeft: '6px' } }, { default: () => 'HOME' }) : null]) },
  { title: 'Slug', key: 'slug' },
  { title: 'Type', key: 'page_type' },
  {
    title: 'Status',
    key: 'status',
    render: row =>
      h(NTag, { type: row.status === 'published' ? 'success' : 'default', size: 'small' }, { default: () => row.status })
  },
  {
    title: 'Updated',
    key: 'updated_at',
    render: row => (row.updated_at ? new Date(row.updated_at).toLocaleString() : '-')
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 420,
    render: row =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', type: 'primary', onClick: () => router.push(`/site/decoration/editor/${row.id}`) }, { default: () => 'Edit' }),
        h(NButton, { size: 'tiny', onClick: () => preview(row) }, { default: () => 'Preview' }),
        h(NButton, { size: 'tiny', type: row.status === 'published' ? 'warning' : 'success', onClick: () => togglePublish(row) }, { default: () => (row.status === 'published' ? 'Unpublish' : 'Publish') }),
        h(NButton, { size: 'tiny', onClick: () => duplicate(row) }, { default: () => 'Copy' }),
        h(NButton, { size: 'tiny', disabled: row.is_default, onClick: () => setDefault(row) }, { default: () => 'Set Home' }),
        h(
          NPopconfirm,
          { onPositiveClick: () => remove(row) },
          {
            trigger: () => h(NButton, { size: 'tiny', type: 'error' }, { default: () => 'Del' }),
            default: () => 'Delete this page?'
          }
        )
      ])
  }
];

onMounted(fetch);
</script>
