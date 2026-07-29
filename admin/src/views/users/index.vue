<template>
  <div class="flex flex-col gap-4">
    <NDataTable :columns="columns" :data="users" :loading="loading" :bordered="false" size="small" />

    <NModal :show="!!roleUser" preset="card" :title="$t('page.users.changeRole')" style="width:420px" @update:show="(v) => { if (!v) roleUser = null; }">
      <div class="flex flex-col gap-3">
        <div><span class="text-[var(--n-text-color-3)]">User: </span>{{ roleUser?.email }}</div>
        <div>
          <span class="text-[var(--n-text-color-3)]">Current Role: </span>
          <NTag :type="roleTagType(roleUser?.role)" size="small">{{ roleUser?.role }}</NTag>
        </div>
        <div>
          <NSelect v-model:value="newRole" :options="roleOptions" :placeholder="$t('page.users.selectRole')" style="width:160px" />
        </div>
        <div v-if="modalError" class="text-red-500 text-sm">{{ modalError }}</div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="roleUser = null">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="modalLoading" @click="updateRole">{{ $t('common.save') }}</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NDataTable, NModal, NSelect, NSpace, NTag } from 'naive-ui';
import { get, post } from '@/service/api/helper';
import { useAuthStore } from '@/store/modules/auth';
import type { DataTableColumns } from 'naive-ui';

const authStore = useAuthStore();
const currentUser = computed(() => authStore.userInfo);

const { t } = useI18n();
const isAdmin = computed(() => currentUser.value?.role === 'ADMIN');

const loading = ref(false);
const users = ref<any[]>([]);
const roleUser = ref<any>(null);
const newRole = ref('');
const modalError = ref('');
const modalLoading = ref(false);

const roleOptions = [
  { label: 'USER', value: 'USER' },
  { label: 'ADMIN', value: 'ADMIN' },
  { label: 'OPERATOR', value: 'OPERATOR' },
  { label: 'SUPPORT', value: 'SUPPORT' },
];

function roleTagType(r: string) {
  const map: Record<string, any> = { ADMIN: 'error', OPERATOR: 'warning', SUPPORT: 'info', USER: 'default' };
  return map[r] || 'default';
}

function formatDate(s: string) { return s ? new Date(s).toLocaleDateString() : '-'; }

function openRoleModal(u: any) {
  roleUser.value = u;
  newRole.value = u.role || 'USER';
  modalError.value = '';
}

async function updateRole() {
  modalLoading.value = true;
  try {
    await post(`/api/admin/v1/users/${roleUser.value.id}/role`, { role: newRole.value });
    roleUser.value = null;
    fetch();
  } catch (e: any) {
    modalError.value = e.response?.data?.detail || 'Update failed';
  } finally { modalLoading.value = false; }
}

const columns: DataTableColumns<any> = [
  { title: t('common.userId'), key: 'id', render: row => (row.id || '').slice(0, 8) },
  { title: t('common.name'), key: 'name', render: row => row.name || row.email || '-' },
  { title: t('page.users.email'), key: 'email' },
  { title: t('page.users.role'), key: 'role', render: row => h(NTag, { type: roleTagType(row.role), size: 'small' }, { default: () => row.role }) },
  { title: t('common.enforce'), key: 'role_enforced', render: row => row.role_enforced ? t('common.yes') : t('common.no') },
  { title: t('common.created'), key: 'created_at', render: row => formatDate(row.created_at) },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => isAdmin.value && row.id !== currentUser.value?.id
      ? h(NButton, { size: 'small', onClick: () => openRoleModal(row) }, { default: () => t('page.users.changeRole') })
      : null,
  },
];

async function fetch() {
  loading.value = true;
  try {
    const res = await get('/api/admin/v1/users/');
    users.value = res.data?.items || res.data || [];
  } finally { loading.value = false; }
}

onMounted(fetch);
</script>
