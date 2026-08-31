<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue';
import {
  NButton,
  NDataTable,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSpace,
  NTag,
  useMessage
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { catalogApi } from '@/service/api/catalog';

const message = useMessage();
const loading = ref(false);
const tree = ref<any[]>([]);

// ---------- 新增 / 编辑表单 ----------
const formVisible = ref(false);
const formLoading = ref(false);
const form = ref<{
  id: number | null;
  parent_id: number | null;
  parent_name: string;
  name: string;
  slug: string;
  icon: string;
  sort: number;
  status: string;
}>({
  id: null,
  parent_id: null,
  parent_name: '',
  name: '',
  slug: '',
  icon: '',
  sort: 0,
  status: 'active'
});

const formTitle = computed(() => {
  if (form.value.id != null) return '编辑分类';
  return form.value.parent_id != null ? `新增子分类（${form.value.parent_name || '父分类'}）` : '新增一级分类';
});

async function fetch() {
  loading.value = true;
  try {
    const res: any = await catalogApi.listCategories();
    tree.value = res?.data?.data ?? res?.data ?? [];
  } finally {
    loading.value = false;
  }
}

function openCreate(parent?: any) {
  form.value = {
    id: null,
    parent_id: parent?.id ?? null,
    parent_name: parent?.name ?? '',
    name: '',
    slug: '',
    icon: '',
    sort: 0,
    status: 'active'
  };
  formVisible.value = true;
}

function openEdit(row: any) {
  form.value = {
    id: row.id,
    parent_id: row.parent_id ?? null,
    parent_name: '',
    name: row.name,
    slug: row.slug ?? '',
    icon: row.icon ?? '',
    sort: row.sort ?? 0,
    status: row.status ?? 'active'
  };
  formVisible.value = true;
}

function closeForm() {
  formVisible.value = false;
}

async function submitForm() {
  if (!form.value.name.trim()) {
    message.warning('请填写分类名称');
    return;
  }
  formLoading.value = true;
  try {
    const payload: Record<string, any> = {
      name: form.value.name.trim(),
      slug: form.value.slug.trim() || undefined,
      icon: form.value.icon.trim() || undefined,
      sort: form.value.sort ?? 0,
      status: form.value.status
    };
    if (form.value.id != null) {
      await catalogApi.updateCategory(form.value.id, payload);
      message.success('分类已更新');
    } else {
      await catalogApi.createCategory({ ...payload, parent_id: form.value.parent_id ?? undefined });
      message.success('分类已创建');
    }
    closeForm();
    fetch();
  } catch {
    // 请求层已弹出错误详情
  } finally {
    formLoading.value = false;
  }
}

async function toggleStatus(row: any) {
  const next = row.status === 'active' ? 'inactive' : 'active';
  try {
    await catalogApi.updateCategory(row.id, { status: next });
    row.status = next;
  } catch {
    // 请求层已提示
  }
}

async function handleDelete(row: any) {
  if (!confirm(`确认删除分类「${row.name}」？`)) return;
  try {
    await catalogApi.deleteCategory(row.id);
    message.success('分类已删除');
    fetch();
  } catch {
    // 请求层已提示（存在子分类 / 商品引用保护）
  }
}

const columns: DataTableColumns<any> = [
  {
    title: '分类名称',
    key: 'name',
    minWidth: 220,
    render: row =>
      h('span', { class: 'inline-flex items-center gap-1' }, [
        row.icon ? h('span', { class: 'text-base' }, row.icon) : null,
        h('span', {}, row.name)
      ])
  },
  { title: 'Slug', key: 'slug', width: 180, render: row => row.slug || '-' },
  {
    title: '层级',
    key: 'level',
    width: 90,
    render: row =>
      h(
        NTag,
        { size: 'small', type: row.level === 1 ? 'primary' : 'info' },
        { default: () => (row.level === 1 ? '一级' : '二级') }
      )
  },
  { title: '排序', key: 'sort', width: 80 },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: row =>
      h(
        NTag,
        { size: 'small', type: row.status === 'active' ? 'success' : 'default' },
        { default: () => (row.status === 'active' ? '启用' : '停用') }
      )
  },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    render: row => {
      const btns = [
        h(NButton, { size: 'tiny', onClick: () => openCreate(row) }, { default: () => '新增子分类' }),
        h(NButton, { size: 'tiny', onClick: () => openEdit(row) }, { default: () => '编辑' }),
        h(
          NButton,
          { size: 'tiny', secondary: true, onClick: () => toggleStatus(row) },
          { default: () => (row.status === 'active' ? '停用' : '启用') }
        ),
        h(
          NButton,
          { size: 'tiny', type: 'error', secondary: true, onClick: () => handleDelete(row) },
          { default: () => '删除' }
        )
      ];
      return h(NSpace, { size: 'small' }, { default: () => btns });
    }
  }
];

onMounted(fetch);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <span class="text-sm text-gray-500">商品分类树（一级 / 二级，可用于导航、筛选与 SEO）</span>
      <NButton type="primary" size="small" @click="openCreate()">+ 新增一级分类</NButton>
    </div>

    <NDataTable
      :columns="columns"
      :data="tree"
      :loading="loading"
      :bordered="false"
      size="small"
      :row-key="row => row.id"
    />

    <NModal
      :show="formVisible"
      preset="card"
      :title="formTitle"
      style="width: 520px"
      @update:show="
        (v: boolean) => {
          if (!v) closeForm();
        }
      "
    >
      <div class="flex flex-col gap-4">
        <NFormItem label="分类名称">
          <NInput v-model:value="form.name" placeholder="例如：狗粮、猫砂" />
        </NFormItem>
        <NFormItem label="Slug（留空自动生成）">
          <NInput v-model:value="form.slug" placeholder="例如 dog-food" />
        </NFormItem>
        <NFormItem label="图标（Emoji 或图标字符，可选）">
          <NInput v-model:value="form.icon" placeholder="例如 🐶" />
        </NFormItem>
        <NFormItem label="排序">
          <NInputNumber v-model:value="form.sort" :min="0" style="width: 160px" />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect
            v-model:value="form.status"
            :options="[
              { label: '启用', value: 'active' },
              { label: '停用', value: 'inactive' }
            ]"
            style="width: 160px"
          />
        </NFormItem>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="closeForm">取消</NButton>
          <NButton type="primary" size="small" :loading="formLoading" @click="submitForm">保存</NButton>
        </div>
      </div>
    </NModal>
  </div>
</template>
