<script setup lang="ts">
import { ref, h, onMounted } from 'vue';
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
const types = ref<any[]>([]);

// ---------- 新增 / 编辑基本信息 ----------
const formVisible = ref(false);
const formLoading = ref(false);
const form = ref<{
  id: number | null;
  name: string;
  status: string;
  sort: number;
}>({
  id: null,
  name: '',
  status: 'active',
  sort: 0
});

// ---------- 规格模板编辑器 ----------
const specVisible = ref(false);
const specLoading = ref(false);
const specType = ref<any>(null);
const specRows = ref<{ spec_key: string; sort: number }[]>([]);

async function fetch() {
  loading.value = true;
  try {
    const res: any = await catalogApi.listProductTypes();
    types.value = res?.data?.data ?? res?.data ?? [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  form.value = { id: null, name: '', status: 'active', sort: 0 };
  formVisible.value = true;
}

function openEdit(row: any) {
  form.value = { id: row.id, name: row.name, status: row.status ?? 'active', sort: row.sort ?? 0 };
  formVisible.value = true;
}

function closeForm() {
  formVisible.value = false;
}

async function submitForm() {
  if (!form.value.name.trim()) {
    message.warning('请填写类型名称');
    return;
  }
  formLoading.value = true;
  try {
    const payload: Record<string, any> = {
      name: form.value.name.trim(),
      status: form.value.status,
      sort: form.value.sort ?? 0
    };
    if (form.value.id != null) {
      await catalogApi.updateProductType(form.value.id, payload);
      message.success('商品类型已更新');
    } else {
      await catalogApi.createProductType(payload);
      message.success('商品类型已创建');
    }
    closeForm();
    fetch();
  } catch {
    // 请求层已提示
  } finally {
    formLoading.value = false;
  }
}

// ---------- 规格模板 ----------
function openSpecEditor(row: any) {
  specType.value = row;
  specRows.value = (row.specs || []).map((s: any) => ({ spec_key: s.spec_key, sort: s.sort ?? 0 }));
  specVisible.value = true;
}

function closeSpecEditor() {
  specVisible.value = false;
  specType.value = null;
}

function addSpecRow() {
  specRows.value.push({ spec_key: '', sort: specRows.value.length });
}

function removeSpecRow(idx: number) {
  specRows.value.splice(idx, 1);
}

async function saveSpecs() {
  const specs = specRows.value
    .map((s, idx) => ({ spec_key: s.spec_key.trim(), sort: s.sort ?? idx }))
    .filter(s => s.spec_key);
  if (specs.some(s => s.spec_key.length > 50)) {
    message.warning('规格键长度不能超过 50 字符');
    return;
  }
  specLoading.value = true;
  try {
    await catalogApi.updateProductType(specType.value.id, { specs });
    message.success('规格模板已保存');
    closeSpecEditor();
    fetch();
  } catch {
    // 请求层已提示
  } finally {
    specLoading.value = false;
  }
}

async function handleDelete(row: any) {
  if (!confirm(`确认删除商品类型「${row.name}」？`)) return;
  try {
    await catalogApi.deleteProductType(row.id);
    message.success('商品类型已删除');
    fetch();
  } catch {
    // 请求层已提示（商品引用保护）
  }
}

const columns: DataTableColumns<any> = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '类型名称', key: 'name', minWidth: 160 },
  {
    title: '规格键模板',
    key: 'specs',
    minWidth: 240,
    render: row => {
      const specs = row.specs || [];
      if (!specs.length) {
        return h('span', { class: 'text-gray-400' }, '未配置');
      }
      return h(
        'span',
        {},
        specs.map((s: any) => h(NTag, { size: 'tiny', style: { margin: '1px 2px' } }, { default: () => s.spec_key }))
      );
    }
  },
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
  { title: '排序', key: 'sort', width: 80 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: row =>
      h(
        NSpace,
        { size: 'small' },
        {
          default: () => [
            h(NButton, { size: 'tiny', onClick: () => openEdit(row) }, { default: () => '编辑' }),
            h(
              NButton,
              { size: 'tiny', type: 'primary', secondary: true, onClick: () => openSpecEditor(row) },
              { default: () => '规格模板' }
            ),
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
      <span class="text-sm text-gray-500">商品类型 = 规格模板头，规格键在新建商品时带出（可增删）</span>
      <NButton type="primary" size="small" @click="openCreate">+ 新增商品类型</NButton>
    </div>

    <NDataTable
      :columns="columns"
      :data="types"
      :loading="loading"
      :bordered="false"
      size="small"
      :row-key="row => row.id"
    />

    <!-- 基本信息表单 -->
    <NModal
      :show="formVisible"
      preset="card"
      :title="form.id != null ? '编辑商品类型' : '新增商品类型'"
      style="width: 480px"
      @update:show="
        (v: boolean) => {
          if (!v) closeForm();
        }
      "
    >
      <div class="flex flex-col gap-4">
        <NFormItem label="类型名称">
          <NInput v-model:value="form.name" placeholder="例如：狗粮、猫砂" />
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
        <NFormItem label="排序">
          <NInputNumber v-model:value="form.sort" :min="0" style="width: 160px" />
        </NFormItem>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="closeForm">取消</NButton>
          <NButton type="primary" size="small" :loading="formLoading" @click="submitForm">保存</NButton>
        </div>
      </div>
    </NModal>

    <!-- 规格模板编辑器 -->
    <NModal
      :show="specVisible"
      preset="card"
      :title="`规格模板：${specType?.name || ''}`"
      style="width: 560px"
      @update:show="
        (v: boolean) => {
          if (!v) closeSpecEditor();
        }
      "
    >
      <div class="flex flex-col gap-3">
        <div class="flex items-center gap-2 px-1 text-xs text-gray-400">
          <span class="flex-1">规格键（如 color / size）</span>
          <span class="w-20">排序</span>
          <span class="w-14"></span>
        </div>
        <div v-for="(row, idx) in specRows" :key="idx" class="flex items-center gap-2">
          <NInput v-model:value="row.spec_key" placeholder="例如 color" class="flex-1" />
          <NInputNumber v-model:value="row.sort" :min="0" style="width: 80px" />
          <NButton size="tiny" type="error" secondary @click="removeSpecRow(idx)">删除</NButton>
        </div>
        <NButton size="small" dashed @click="addSpecRow">+ 添加规格键</NButton>
        <div class="flex justify-end gap-2 mt-2">
          <NButton size="small" @click="closeSpecEditor">取消</NButton>
          <NButton type="primary" size="small" :loading="specLoading" @click="saveSpecs">保存模板</NButton>
        </div>
      </div>
    </NModal>
  </div>
</template>
