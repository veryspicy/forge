<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue';
import {
  NButton, NCheckbox, NDataTable, NFormItem, NInput, NModal, NSpace, NTag,
} from 'naive-ui';
import { del, get, post, put } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const roles = ref<any[]>([]);
const searchText = ref('');
const allPerms = ref<any[]>([]);

// Form state
const formRole = ref<any>(null);
const formName = ref('');
const formDisplayName = ref('');
const formDescription = ref('');
const formPermIds = ref<string[]>([]);
const formError = ref('');
const formLoading = ref(false);

const permModules = computed(() => {
  const map: Record<string, any[]> = {};
  for (const p of allPerms.value) {
    const mod = p.module || '其他';
    if (!map[mod]) map[mod] = [];
    map[mod].push(p);
  }
  return Object.entries(map).map(([module, perms]) => ({ module, permissions: perms }));
});

function togglePerm(id: string, checked: boolean) {
  if (checked) {
    formPermIds.value = [...formPermIds.value, id];
  } else {
    formPermIds.value = formPermIds.value.filter(x => x !== id);
  }
}

async function fetchPerms() {
  try {
    const res = await get('/api/admin/v1/roles/permissions');
    allPerms.value = res.data?.permissions || [];
  } catch { /* ignore */ }
}

async function fetch() {
  loading.value = true;
  try {
    const params: any = {};
    if (searchText.value) params.search = searchText.value;
    const res = await get('/api/admin/v1/roles/', params);
    roles.value = res.data?.items || [];
  } finally {
    loading.value = false;
  }
}

function openCreateModal() {
  formRole.value = {};
  formName.value = '';
  formDisplayName.value = '';
  formDescription.value = '';
  formPermIds.value = [];
  formError.value = '';
}

function openEditModal(r: any) {
  formRole.value = r;
  formName.value = r.name;
  formDisplayName.value = r.display_name;
  formDescription.value = r.description || '';
  formPermIds.value = (r.permissions || []).map((p: any) => p.id);
  formError.value = '';
}

function closeForm() {
  formRole.value = null;
}

async function submitForm() {
  formLoading.value = true;
  formError.value = '';
  try {
    if (formRole.value?.id) {
      await put(`/api/admin/v1/roles/${formRole.value.id}`, {
        display_name: formDisplayName.value || undefined,
        description: formDescription.value || undefined,
        permission_ids: formPermIds.value,
      });
    } else {
      await post('/api/admin/v1/roles/', {
        name: formName.value,
        display_name: formDisplayName.value,
        description: formDescription.value,
        permission_ids: formPermIds.value,
      });
    }
    closeForm();
    fetch();
  } catch (e: any) {
    formError.value = e.response?.data?.detail || '操作失败';
  } finally {
    formLoading.value = false;
  }
}

async function handleDelete(r: any) {
  if (r.is_system) {
    alert('系统角色不可删除');
    return;
  }
  if (!confirm(`确认删除角色 "${r.display_name || r.name}"？`)) return;
  try {
    await del(`/api/admin/v1/roles/${r.id}`);
    fetch();
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败');
  }
}

const columns: DataTableColumns<any> = [
  { title: '名称', key: 'name', width: 160 },
  { title: '显示名', key: 'display_name', width: 160 },
  { title: '描述', key: 'description', width: 220, render: (row) => row.description || '-' },
  {
    title: '系统', key: 'is_system', width: 80,
    render: (row) =>
      h(NTag, { type: row.is_system ? 'warning' : 'default', size: 'small' }, { default: () => row.is_system ? '系统' : '自定义' }),
  },
  {
    title: '权限', key: 'permissions', minWidth: 300,
    render: (row) => {
      const tags = (row.permissions || []).map((p: any) =>
        h(NTag, { size: 'tiny', style: { margin: '1px 2px' } }, { default: () => p.display_name || p.code })
      );
      return h('span', tags);
    },
  },
  {
    title: '操作', key: 'actions', width: 160,
    render: (row) => {
      const btns = [
        h(NButton, { size: 'tiny', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
      ];
      if (!row.is_system) {
        btns.push(
          h(NButton, { size: 'tiny', type: 'error', secondary: true, onClick: () => handleDelete(row) }, { default: () => '删除' }),
        );
      }
      return h(NSpace, { size: 'small' }, { default: () => btns });
    },
  },
];

onMounted(() => {
  fetchPerms();
  fetch();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Toolbar -->
    <div class="flex items-center gap-3">
      <NInput
        v-model:value="searchText"
        placeholder="搜索角色..."
        clearable
        style="width: 240px"
        @keyup.enter="fetch"
      />
      <NButton size="small" @click="fetch">搜索</NButton>
      <NButton type="primary" size="small" @click="openCreateModal">
        + 新增角色
      </NButton>
    </div>

    <!-- Table -->
    <NDataTable
      :columns="columns"
      :data="roles"
      :loading="loading"
      :bordered="false"
      size="small"
    />

    <!-- Create / Edit Modal -->
    <NModal
      :show="!!formRole"
      preset="card"
      :title="formRole?.id ? '编辑角色' : '新增角色'"
      style="width:600px"
      @update:show="(v: boolean) => { if (!v) closeForm(); }"
    >
      <div class="flex flex-col gap-4">
        <NFormItem label="角色名称">
          <NInput v-model:value="formName" placeholder="例如 warehouse_admin" :disabled="!!formRole?.id" />
        </NFormItem>
        <NFormItem label="显示名称">
          <NInput v-model:value="formDisplayName" placeholder="例如 仓库管理员" />
        </NFormItem>
        <NFormItem label="描述">
          <NInput v-model:value="formDescription" placeholder="该角色的职责说明..." />
        </NFormItem>
        <div>
          <div class="text-sm mb-2 text-[var(--n-text-color-3)] font-medium">权限</div>
          <div v-for="mod in permModules" :key="mod.module" class="mb-3">
            <div class="text-xs font-semibold uppercase mb-1 text-[var(--n-text-color-3)]">
              {{ mod.module }}
            </div>
            <div class="flex flex-wrap gap-1">
              <NCheckbox
                v-for="perm in mod.permissions"
                :key="perm.id"
                :checked="formPermIds.includes(perm.id)"
                @update:checked="(v: boolean) => togglePerm(perm.id, v)"
              >
                {{ perm.display_name || perm.code }}
              </NCheckbox>
            </div>
          </div>
        </div>
        <div v-if="formError" class="text-red-500 text-sm">{{ formError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="closeForm">取消</NButton>
          <NButton type="primary" :loading="formLoading" @click="submitForm">
            {{ formRole?.id ? '保存' : '创建' }}
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
