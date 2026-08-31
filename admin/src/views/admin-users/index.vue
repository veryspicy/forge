<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue';
import { NButton, NDataTable, NInput, NModal, NSelect, NSpace, NSwitch, NTag } from 'naive-ui';
import { del, get, post, put } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const users = ref<any[]>([]);
const searchText = ref('');
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

// Form state
const formUser = ref<any>(null);
const formEmail = ref('');
const formPassword = ref('');
const formDisplayName = ref('');
const formIsActive = ref(true);
const formRoleIds = ref<string[]>([]);
const formError = ref('');
const formLoading = ref(false);

// Role assignment
const roleUser = ref<any>(null);
const assignRoleIds = ref<string[]>([]);
const roleError = ref('');
const roleLoading = ref(false);

// Roles for select
const allRoles = ref<any[]>([]);
const roleSelectOptions = computed(() =>
  allRoles.value.map((r: any) => ({ label: r.display_name || r.name, value: r.id }))
);

const pagination = computed(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  showSizePicker: true,
  pageSizes: [10, 20, 50]
}));

function onPageChange(p: number) {
  page.value = p;
  fetch();
}
function onPageSizeChange(s: number) {
  pageSize.value = s;
  page.value = 1;
  fetch();
}

async function fetchRoles() {
  try {
    const res = await get('/api/admin/v1/roles/');
    allRoles.value = res.data?.items || [];
  } catch {
    /* ignore */
  }
}

async function fetch() {
  loading.value = true;
  try {
    const params: any = { page: page.value, page_size: pageSize.value };
    if (searchText.value) params.search = searchText.value;
    const res = await get('/api/admin/v1/admin-users/', params);
    users.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

function openCreateModal() {
  formUser.value = {};
  formEmail.value = '';
  formPassword.value = '';
  formDisplayName.value = '';
  formIsActive.value = true;
  formRoleIds.value = [];
  formError.value = '';
}

function openEditModal(u: any) {
  formUser.value = u;
  formEmail.value = u.email;
  formPassword.value = '';
  formDisplayName.value = u.display_name;
  formIsActive.value = u.is_active;
  formRoleIds.value = (u.roles || []).map((r: any) => r.id);
  formError.value = '';
}

function closeForm() {
  formUser.value = null;
}

async function submitForm() {
  formLoading.value = true;
  formError.value = '';
  try {
    if (formUser.value?.id) {
      // Update
      await put(`/api/admin/v1/admin-users/${formUser.value.id}`, {
        display_name: formDisplayName.value || undefined,
        is_active: formIsActive.value,
        password: formPassword.value || undefined
      });
      // Update roles
      await put(`/api/admin/v1/admin-users/${formUser.value.id}/roles`, {
        role_ids: formRoleIds.value
      });
    } else {
      // Create
      await post('/api/admin/v1/admin-users/', {
        email: formEmail.value,
        password: formPassword.value,
        display_name: formDisplayName.value,
        role_ids: formRoleIds.value
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

async function handleDelete(u: any) {
  if (!confirm(`确认删除管理员 "${u.email}"？`)) return;
  try {
    await del(`/api/admin/v1/admin-users/${u.id}`);
    fetch();
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败');
  }
}

function openRoleModal(u: any) {
  roleUser.value = u;
  assignRoleIds.value = (u.roles || []).map((r: any) => r.id);
  roleError.value = '';
}

async function assignRoles() {
  roleLoading.value = true;
  roleError.value = '';
  try {
    await put(`/api/admin/v1/admin-users/${roleUser.value.id}/roles`, {
      role_ids: assignRoleIds.value
    });
    roleUser.value = null;
    fetch();
  } catch (e: any) {
    roleError.value = e.response?.data?.detail || '分配失败';
  } finally {
    roleLoading.value = false;
  }
}

const columns: DataTableColumns<any> = [
  { title: '邮箱', key: 'email', width: 220 },
  { title: '名称', key: 'display_name', width: 140 },
  {
    title: '角色',
    key: 'roles',
    width: 200,
    render: row => {
      const roleEls = (row.roles || []).map((r: any) =>
        h(NTag, { size: 'small', style: { marginRight: '4px' } }, { default: () => r.display_name || r.name })
      );
      return h('span', roleEls);
    }
  },
  {
    title: '状态',
    key: 'is_active',
    width: 80,
    render: row =>
      h(
        NTag,
        { type: row.is_active ? 'success' : 'default', size: 'small' },
        { default: () => (row.is_active ? '启用' : '禁用') }
      )
  },
  {
    title: '最后登录',
    key: 'last_login_at',
    width: 150,
    render: row => (row.last_login_at ? new Date(row.last_login_at).toLocaleString() : '-')
  },
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
            h(NButton, { size: 'tiny', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
            h(NButton, { size: 'tiny', onClick: () => openRoleModal(row) }, { default: () => '角色' }),
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

onMounted(() => {
  fetchRoles();
  fetch();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Toolbar -->
    <div class="flex items-center gap-3">
      <NInput
        v-model:value="searchText"
        placeholder="搜索邮箱或名称..."
        clearable
        style="width: 280px"
        @keyup.enter="fetch"
      />
      <NButton size="small" @click="fetch">搜索</NButton>
      <NButton type="primary" size="small" @click="openCreateModal">+ 新增管理员</NButton>
    </div>

    <!-- Table -->
    <NDataTable
      :columns="columns"
      :data="users"
      :loading="loading"
      :bordered="false"
      size="small"
      :pagination="pagination"
      @update:page="onPageChange"
      @update:page-size="onPageSizeChange"
    />

    <!-- Create / Edit Modal -->
    <NModal
      :show="!!formUser"
      preset="card"
      :title="formUser?.id ? '编辑管理员' : '新增管理员'"
      style="width: 480px"
      @update:show="
        (v: boolean) => {
          if (!v) closeForm();
        }
      "
    >
      <div class="flex flex-col gap-4">
        <div>
          <div class="text-sm mb-1 text-[var(--n-text-color-3)]">邮箱</div>
          <NInput v-model:value="formEmail" placeholder="admin@example.com" :disabled="!!formUser?.id" />
        </div>
        <div v-if="!formUser?.id">
          <div class="text-sm mb-1 text-[var(--n-text-color-3)]">密码</div>
          <NInput v-model:value="formPassword" type="password" placeholder="至少6位" />
        </div>
        <div>
          <div class="text-sm mb-1 text-[var(--n-text-color-3)]">显示名称</div>
          <NInput v-model:value="formDisplayName" placeholder="显示名称" />
        </div>
        <div v-if="formUser?.id">
          <div class="text-sm mb-1 text-[var(--n-text-color-3)]">状态</div>
          <NSwitch v-model:value="formIsActive" />
          <span class="ml-2 text-sm">{{ formIsActive ? '启用' : '禁用' }}</span>
        </div>
        <div>
          <div class="text-sm mb-1 text-[var(--n-text-color-3)]">角色</div>
          <NSelect v-model:value="formRoleIds" :options="roleSelectOptions" multiple placeholder="选择角色..." />
        </div>
        <div v-if="formError" class="text-red-500 text-sm">{{ formError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="closeForm">取消</NButton>
          <NButton type="primary" :loading="formLoading" @click="submitForm">
            {{ formUser?.id ? '保存' : '创建' }}
          </NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Role Assignment Modal -->
    <NModal
      :show="!!roleUser"
      preset="card"
      title="分配角色"
      style="width: 460px"
      @update:show="
        (v: boolean) => {
          if (!v) roleUser = null;
        }
      "
    >
      <div class="flex flex-col gap-3">
        <div>
          <span class="text-[var(--n-text-color-3)]">用户：</span>
          {{ roleUser?.email }}
        </div>
        <NSelect v-model:value="assignRoleIds" :options="roleSelectOptions" multiple placeholder="选择角色" />
        <div v-if="roleError" class="text-red-500 text-sm">{{ roleError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="roleUser = null">取消</NButton>
          <NButton type="primary" :loading="roleLoading" @click="assignRoles">保存</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
