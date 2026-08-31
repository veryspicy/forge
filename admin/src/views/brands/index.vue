<script setup lang="ts">
import { ref, h, onMounted } from 'vue';
import { NButton, NDataTable, NFormItem, NInput, NInputNumber, NModal, NSpace, NSwitch, useMessage } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { catalogApi } from '@/service/api/catalog';
import { resourceApi } from '@/service/api/resources';

const message = useMessage();
const loading = ref(false);
const brands = ref<any[]>([]);

// ---------- 新增 / 编辑表单 ----------
const formVisible = ref(false);
const formLoading = ref(false);
const form = ref<{
  id: number | null;
  name: string;
  logo: string;
  show_status: boolean;
  sort: number;
}>({
  id: null,
  name: '',
  logo: '',
  show_status: true,
  sort: 0
});

const logoUploading = ref(false);
const logoInput = ref<HTMLInputElement | null>(null);

async function fetch() {
  loading.value = true;
  try {
    const res: any = await catalogApi.listBrands();
    brands.value = res?.data?.data ?? res?.data ?? [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  form.value = { id: null, name: '', logo: '', show_status: true, sort: 0 };
  formVisible.value = true;
}

function openEdit(row: any) {
  form.value = {
    id: row.id,
    name: row.name,
    logo: row.logo ?? '',
    show_status: !!row.show_status,
    sort: row.sort ?? 0
  };
  formVisible.value = true;
}

function closeForm() {
  formVisible.value = false;
}

function triggerLogoSelect() {
  logoInput.value?.click();
}

async function onLogoFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  logoUploading.value = true;
  try {
    const res: any = await resourceApi.upload(file, { directory: 'brands' });
    const data = res?.data?.data ?? res?.data;
    const url = data?.url;
    if (url) {
      form.value.logo = url;
      message.success('Logo 上传成功');
    } else {
      message.error('上传成功但未取到图片地址');
    }
  } catch {
    // 请求层已提示
  } finally {
    logoUploading.value = false;
  }
}

async function submitForm() {
  if (!form.value.name.trim()) {
    message.warning('请填写品牌名称');
    return;
  }
  formLoading.value = true;
  try {
    const payload: Record<string, any> = {
      name: form.value.name.trim(),
      logo: form.value.logo.trim() || undefined,
      show_status: form.value.show_status,
      sort: form.value.sort ?? 0
    };
    if (form.value.id != null) {
      await catalogApi.updateBrand(form.value.id, payload);
      message.success('品牌已更新');
    } else {
      await catalogApi.createBrand(payload);
      message.success('品牌已创建');
    }
    closeForm();
    fetch();
  } catch {
    // 请求层已提示
  } finally {
    formLoading.value = false;
  }
}

async function toggleShow(row: any, value: boolean) {
  try {
    await catalogApi.updateBrand(row.id, { show_status: value });
    row.show_status = value;
  } catch {
    // 请求层已提示
  }
}

async function handleDelete(row: any) {
  if (!confirm(`确认删除品牌「${row.name}」？`)) return;
  try {
    await catalogApi.deleteBrand(row.id);
    message.success('品牌已删除');
    fetch();
  } catch {
    // 请求层已提示（商品引用保护）
  }
}

const columns: DataTableColumns<any> = [
  { title: 'ID', key: 'id', width: 70 },
  {
    title: 'Logo',
    key: 'logo',
    width: 90,
    render: row =>
      row.logo
        ? h('img', {
            src: row.logo,
            class: 'h-9 w-9 rounded object-contain border border-gray-200',
            onError: (e: Event) => {
              (e.target as HTMLImageElement).style.visibility = 'hidden';
            }
          })
        : h('span', { class: 'text-gray-400' }, '-')
  },
  { title: '品牌名称', key: 'name', minWidth: 160 },
  {
    title: '显示状态',
    key: 'show_status',
    width: 110,
    render: row =>
      h(NSwitch, {
        size: 'small',
        value: !!row.show_status,
        onUpdateValue: (v: boolean) => toggleShow(row, v)
      })
  },
  { title: '排序', key: 'sort', width: 80 },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: row =>
      h(
        NSpace,
        { size: 'small' },
        {
          default: () => [
            h(NButton, { size: 'tiny', onClick: () => openEdit(row) }, { default: () => '编辑' }),
            h(
              NButton,
              { size: 'tiny', type: 'error', secondary: true, onClick: () => handleDelete(row) },
              { default: () => '删除' }
            )
          ]
        }
      )
  }
];

onMounted(fetch);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <span class="text-sm text-gray-500">自营供应链轻量品牌（名称 + Logo + 显示开关）</span>
      <NButton type="primary" size="small" @click="openCreate">+ 新增品牌</NButton>
    </div>

    <NDataTable
      :columns="columns"
      :data="brands"
      :loading="loading"
      :bordered="false"
      size="small"
      :row-key="row => row.id"
    />

    <NModal
      :show="formVisible"
      preset="card"
      :title="form.id != null ? '编辑品牌' : '新增品牌'"
      style="width: 520px"
      @update:show="
        (v: boolean) => {
          if (!v) closeForm();
        }
      "
    >
      <div class="flex flex-col gap-4">
        <NFormItem label="品牌名称">
          <NInput v-model:value="form.name" placeholder="例如：ForgePet" />
        </NFormItem>
        <NFormItem label="Logo">
          <div class="flex items-center gap-2 w-full">
            <NInput v-model:value="form.logo" placeholder="图片 URL" />
            <NButton size="small" :loading="logoUploading" @click="triggerLogoSelect">上传</NButton>
            <input ref="logoInput" type="file" accept="image/*" class="hidden" @change="onLogoFileChange" />
          </div>
          <div v-if="form.logo" class="mt-1">
            <img :src="form.logo" class="h-12 w-12 rounded border border-gray-200 object-contain" />
          </div>
        </NFormItem>
        <NFormItem label="显示状态">
          <NSwitch v-model:value="form.show_status" />
        </NFormItem>
        <NFormItem label="排序">
          <NInputNumber v-model:value="form.sort" :min="0" style="width: 160px" />
        </NFormItem>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="closeForm">取消</NButton>
          <NButton type="primary" size="small" :loading="formLoading" @click="submitForm">保存</NButton>
        </div>
      </div>
    </NModal>
  </div>
</template>
