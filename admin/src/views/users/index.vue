<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NSwitch,
  NTag,
  useMessage
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { del, get, post, put } from '@/service/api/helper';
import { useAuthStore } from '@/store/modules/auth';

const authStore = useAuthStore();
const { t } = useI18n();
const message = useMessage();

const can = (perm: string) => {
  const perms = authStore.userInfo.permissions || [];
  // super_admin 通配符：permissions 含 '*' 时放行任意权限码
  return perms.includes('*') || perms.includes(perm);
};
const canManage = computed(() => can('users:manage'));

const loading = ref(false);
const rows = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const keyword = ref('');
const status = ref('');

const statusOptions = [
  { label: t('page.users.allStatus'), value: '' },
  { label: t('page.users.active'), value: 'active' },
  { label: t('page.users.disabled'), value: 'disabled' }
];

const pagination = computed(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  showSizePicker: true,
  pageSizes: [10, 20, 50]
}));

// create / edit modal
const formShow = ref(false);
const formMode = ref<'create' | 'edit'>('create');
const editingId = ref<string | null>(null);
const form = ref({ email: '', password: '', name: '', phone: '', is_active: true });
const formSaving = ref(false);

// reset password modal
const resetUser = ref<any>(null);
const newPassword = ref('');
const resetSaving = ref(false);

// detail drawer
const drawerShow = ref(false);
const detail = ref<any>(null);
const detailLoading = ref(false);

function fmtDate(s?: string) {
  return s ? new Date(s).toLocaleString() : '-';
}

function statusTag(row: any) {
  return row.is_active
    ? h(NTag, { type: 'success', size: 'small' }, { default: () => t('page.users.active') })
    : h(NTag, { type: 'error', size: 'small' }, { default: () => t('page.users.disabled') });
}

function openDetail(row: any) {
  drawerShow.value = true;
  detail.value = null;
  detailLoading.value = true;
  get(`/api/admin/v1/users/${row.id}`)
    .then(res => {
      detail.value = res.data;
    })
    .finally(() => {
      detailLoading.value = false;
    });
}

function closeDetail() {
  drawerShow.value = false;
  detail.value = null;
}

function openCreate() {
  formMode.value = 'create';
  editingId.value = null;
  form.value = { email: '', password: '', name: '', phone: '', is_active: true };
  formShow.value = true;
}

function openEdit(row: any) {
  formMode.value = 'edit';
  editingId.value = row.id;
  form.value = {
    email: row.email || '',
    password: '',
    name: row.name || '',
    phone: row.phone || '',
    is_active: row.is_active ?? true
  };
  formShow.value = true;
}

async function submitForm() {
  if (!form.value.email || !form.value.name || (formMode.value === 'create' && !form.value.password)) {
    message.warning(t('common.requiredText') || 'Missing required fields');
    return;
  }
  formSaving.value = true;
  try {
    if (formMode.value === 'create') {
      await post('/api/admin/v1/users/', {
        email: form.value.email.trim(),
        password: form.value.password,
        name: form.value.name.trim(),
        phone: form.value.phone.trim(),
        is_active: form.value.is_active
      });
      message.success(t('page.users.created'));
    } else {
      await put(`/api/admin/v1/users/${editingId.value}`, {
        email: form.value.email.trim(),
        name: form.value.name.trim(),
        phone: form.value.phone.trim(),
        is_active: form.value.is_active
      });
      message.success(t('page.users.saved'));
      if (drawerShow.value && detail.value?.id === editingId.value) {
        openDetail({ id: editingId.value });
      }
    }
    formShow.value = false;
    await fetch();
  } finally {
    formSaving.value = false;
  }
}

function openReset(row: any) {
  resetUser.value = row;
  newPassword.value = '';
}

async function submitReset() {
  if (!newPassword.value || newPassword.value.length < 6) {
    message.warning(t('page.users.passwordPlaceholder'));
    return;
  }
  resetSaving.value = true;
  try {
    await put(`/api/admin/v1/users/${resetUser.value.id}/password`, { password: newPassword.value });
    message.success(t('page.users.resetSuccess'));
    resetUser.value = null;
  } finally {
    resetSaving.value = false;
  }
}

function toggleFreeze(row: any) {
  const action = row.is_active ? t('page.users.freeze') : t('page.users.unfreeze');
  if (!window.confirm(t('page.users.freezeConfirm', { email: row.email }))) return;
  put(`/api/admin/v1/users/${row.id}`, { is_active: !row.is_active })
    .then(() => {
      message.success(action);
      fetch();
      if (drawerShow.value && detail.value?.id === row.id) {
        openDetail(row);
      }
    })
    .catch(() => undefined);
}

function remove(row: any) {
  if (!window.confirm(t('page.users.deleteConfirm', { email: row.email }))) return;
  del(`/api/admin/v1/users/${row.id}`)
    .then(() => {
      message.success(t('page.users.deleteSuccess'));
      if (drawerShow.value && detail.value?.id === row.id) {
        closeDetail();
      }
      fetch();
    })
    .catch(() => undefined);
}

// 管理操作统一收敛到客户资料抽屉（点 email 进入），列表不渲染操作列，避免与抽屉内操作重复。
// 后续如需在列表提供高频且安全的快捷操作（如复制邮箱、导出），在此新增专用列。
const columns = computed<DataTableColumns<any>>(() => {
  const cols: DataTableColumns<any> = [
    {
      title: t('page.users.email'),
      key: 'email',
      minWidth: 200,
      render: row =>
        h(NButton, { text: true, type: 'primary', onClick: () => openDetail(row) }, { default: () => row.email })
    },
    { title: t('page.users.name'), key: 'name', minWidth: 120, render: row => row.name || '-' },
    { title: t('page.users.phone'), key: 'phone', minWidth: 120, render: row => row.phone || '-' },
    {
      title: t('page.users.role'),
      key: 'role',
      width: 100,
      render: () => h(NTag, { size: 'small' }, { default: () => t('page.users.customer') })
    },
    { title: t('page.users.status'), key: 'is_active', width: 100, render: row => statusTag(row) },
    { title: t('page.users.createdAt'), key: 'created_at', width: 170, render: row => fmtDate(row.created_at) }
  ];
  return cols;
});

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value };
    if (keyword.value.trim()) params.keyword = keyword.value.trim();
    if (status.value) params.status = status.value;
    const res = await get('/api/admin/v1/users/', params);
    rows.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

function onPageChange(p: number) {
  page.value = p;
  fetch();
}

function onPageSizeChange(s: number) {
  pageSize.value = s;
  page.value = 1;
  fetch();
}

function onSearch() {
  page.value = 1;
  fetch();
}

let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(onSearch, 400);
});
onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
});

onMounted(fetch);
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <NSpace :size="8">
        <NInput
          v-model:value="keyword"
          clearable
          :placeholder="$t('page.users.searchPlaceholder')"
          style="width: 280px"
        />
        <NSelect v-model:value="status" :options="statusOptions" style="width: 130px" @update:value="onSearch" />
      </NSpace>
      <NButton v-permission="'users:manage'" type="primary" @click="openCreate">
        {{ $t('page.users.addCustomer') }}
      </NButton>
    </div>

    <!-- Table -->
    <NDataTable
      :columns="columns"
      :data="rows"
      :loading="loading"
      :pagination="pagination"
      :bordered="false"
      size="small"
      @update:page="onPageChange"
      @update:page-size="onPageSizeChange"
    />

    <!-- Create / Edit modal -->
    <NModal
      v-model:show="formShow"
      preset="card"
      :title="formMode === 'create' ? $t('page.users.createCustomer') : $t('page.users.editCustomer')"
      style="width: 480px"
    >
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <span class="text-sm">{{ $t('page.users.email') }}</span>
          <NInput v-model:value="form.email" placeholder="user@example.com" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm">{{ $t('page.users.name') }}</span>
          <NInput v-model:value="form.name" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm">{{ $t('page.users.phone') }}</span>
          <NInput v-model:value="form.phone" :placeholder="$t('common.optional')" />
        </div>
        <div v-if="formMode === 'create'" class="flex flex-col gap-1">
          <span class="text-sm">{{ $t('page.users.password') }}</span>
          <NInput
            v-model:value="form.password"
            type="password"
            show-password-on="click"
            :placeholder="$t('page.users.passwordPlaceholder')"
          />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm">{{ $t('page.users.isActive') }}</span>
          <NSwitch v-model:value="form.is_active" />
        </div>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="formShow = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="formSaving" @click="submitForm">{{ $t('common.save') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Reset password modal -->
    <NModal
      :show="!!resetUser"
      preset="card"
      :title="$t('page.users.resetPassword')"
      style="width: 420px"
      @update:show="v => v || (resetUser = null)"
    >
      <div v-if="resetUser" class="flex flex-col gap-3">
        <div class="text-sm text-[var(--n-text-color-3)]">{{ resetUser.email }}</div>
        <NInput
          v-model:value="newPassword"
          type="password"
          show-password-on="click"
          :placeholder="$t('page.users.passwordPlaceholder')"
        />
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="resetUser = null">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="resetSaving" @click="submitReset">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Detail drawer -->
    <NDrawer v-model:show="drawerShow" placement="right" :width="640" @update:show="v => v || closeDetail()">
      <NDrawerContent :title="detail ? $t('page.users.customerProfile') : ''" closable>
        <div v-if="detailLoading" class="py-12 text-center text-sm text-[var(--n-text-color-3)]">
          {{ $t('common.loadingText') }}
        </div>
        <template v-else-if="detail">
          <div v-if="canManage" class="mb-4 flex flex-wrap items-center justify-end gap-2">
            <NButton size="small" @click="openEdit(detail)">{{ $t('page.users.edit') }}</NButton>
            <NButton size="small" :type="detail.is_active ? 'warning' : 'success'" @click="toggleFreeze(detail)">
              {{ detail.is_active ? $t('page.users.freeze') : $t('page.users.unfreeze') }}
            </NButton>
            <NButton size="small" @click="openReset(detail)">{{ $t('page.users.resetPassword') }}</NButton>
            <NButton size="small" type="error" @click="remove(detail)">{{ $t('page.users.delete') }}</NButton>
          </div>

          <NDescriptions :column="1" bordered size="small" class="mb-4">
            <NDescriptionsItem :label="$t('page.users.email')">{{ detail.email }}</NDescriptionsItem>
            <NDescriptionsItem :label="$t('page.users.name')">{{ detail.name || '-' }}</NDescriptionsItem>
            <NDescriptionsItem :label="$t('page.users.phone')">{{ detail.phone || '-' }}</NDescriptionsItem>
            <NDescriptionsItem :label="$t('page.users.role')">
              <NTag size="small">{{ $t('page.users.customer') }}</NTag>
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('page.users.status')">
              <NTag :type="detail.is_active ? 'success' : 'error'" size="small">
                {{ detail.is_active ? $t('page.users.active') : $t('page.users.disabled') }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('page.users.createdAt')">{{ fmtDate(detail.created_at) }}</NDescriptionsItem>
          </NDescriptions>

          <!-- Stats -->
          <NSpace :size="8" class="mb-4">
            <NTag type="info" size="medium">{{ $t('page.users.totalOrders') }}: {{ detail.stats?.orders ?? 0 }}</NTag>
            <NTag type="info" size="medium">{{ $t('page.users.totalPets') }}: {{ detail.stats?.pets ?? 0 }}</NTag>
          </NSpace>

          <!-- Pets -->
          <NDivider title-placement="left">{{ $t('page.users.pets') }}</NDivider>
          <div v-if="detail.pets?.length" class="flex flex-col gap-2">
            <div
              v-for="p in detail.pets"
              :key="p.id"
              class="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-[var(--n-border-color)] px-3 py-2 text-sm"
            >
              <span class="font-medium">{{ p.name }}</span>
              <span class="text-[var(--n-text-color-3)]">{{ p.breed || p.breed_custom || '-' }}</span>
              <span class="text-[var(--n-text-color-3)]">{{ p.gender || '-' }}</span>
              <span v-if="p.weight != null" class="text-[var(--n-text-color-3)]">{{ p.weight }}kg</span>
              <span v-if="p.birthday" class="text-[var(--n-text-color-3)]">{{ fmtDate(p.birthday) }}</span>
            </div>
          </div>
          <NEmpty v-else :description="$t('page.users.noPets')" size="small" />

          <!-- Recent orders -->
          <NDivider title-placement="left">{{ $t('page.users.recentOrders') }}</NDivider>
          <div v-if="detail.orders?.recent?.length" class="flex flex-col gap-2">
            <div
              v-for="o in detail.orders.recent"
              :key="o.id"
              class="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-[var(--n-border-color)] px-3 py-2 text-sm"
            >
              <span class="font-mono">{{ o.order_number }}</span>
              <NTag size="small">{{ o.status }}</NTag>
              <span class="text-[var(--n-text-color-3)]">{{ o.currency }} {{ o.total }}</span>
              <span class="text-[var(--n-text-color-3)]">{{ fmtDate(o.created_at) }}</span>
            </div>
          </div>
          <NEmpty v-else :description="$t('page.users.noOrders')" size="small" />
        </template>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
