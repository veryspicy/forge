<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted, h } from 'vue';
import {
  NButton,
  NDataTable,
  NInput,
  NModal,
  NForm,
  NFormItem,
  NPopconfirm,
  NSelect,
  NSpace,
  NTag
} from 'naive-ui';
import { get, post, patch, del } from '@/service/api/helper';
import { useAuthStore } from '@/store/modules/auth';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const shipments = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statusFilter = ref<string | null>(null);
const keyword = ref('');
const authStore = useAuthStore();
const checkedKeys = ref<string[]>([]);
const archiving = ref(false);
const showModal = ref(false);
const editing = ref<any>(null);
const modalError = ref('');
const modalLoading = ref(false);

const statusOptions = [
  { label: 'PENDING', value: 'PENDING' },
  { label: 'IN TRANSIT', value: 'IN_TRANSIT' },
  { label: 'DELIVERED', value: 'DELIVERED' },
  { label: 'FAILED', value: 'FAILED' }
];

const { t } = useI18n();
const form = ref({
  order_id: '',
  carrier: '',
  tracking_number: '',
  status: 'PENDING',
  estimated_delivery: '',
  origin: '',
  destination: ''
});

function formatDate(s: string) {
  return s ? new Date(s).toLocaleDateString() : '-';
}

/** 归档（后台删除）入口仅对持有 shipments:archive 的角色渲染；super_admin 走权限通配 '*' */
const canArchive = computed(() => {
  const perms = authStore.userInfo.permissions || [];
  return perms.includes('*') || perms.includes('shipments:archive');
});

const columns: DataTableColumns<any> = [
  { title: t('page.orders.orderNumber'), key: 'id', render: row => (row.id || '').slice(0, 8) },
  { title: t('page.shipments.orderId'), key: 'order_id', render: row => (row.order_id || '').slice(0, 8) },
  { title: t('page.shipments.carrier'), key: 'carrier' },
  { title: t('page.shipments.trackingNumber'), key: 'tracking_number' },
  {
    title: t('common.status'),
    key: 'status',
    render: row =>
      h(
        NTag,
        { type: row.status === 'DELIVERED' ? 'success' : row.status === 'FAILED' ? 'error' : 'warning', size: 'small' },
        { default: () => row.status }
      )
  },
  {
    title: t('page.shipments.estimatedDelivery'),
    key: 'estimated_delivery',
    render: row => formatDate(row.estimated_delivery)
  },
  {
    title: t('page.suppliers.actions'),
    key: 'actions',
    render: row =>
      h(NSpace, { size: 4, align: 'center' }, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openModal(row) }, { default: () => t('common.edit') }),
          canArchive.value
            ? h(
                NPopconfirm,
                { onPositiveClick: () => archiveShipments([row.id]) },
                {
                  trigger: () =>
                    h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除' }),
                  default: () => '确认删除该运单？删除后不再出现在列表与看板，可恢复。'
                }
              )
            : null
        ].filter(Boolean)
      })
  }
];

/** 选择列仅在具备归档权限时出现，无权角色看不到多选与批量入口 */
const selectionColumn: DataTableColumns<any>[number] = {
  type: 'selection',
  disabled: (row: any) => !row.id
};

const tableColumns = computed(() => (canArchive.value ? [selectionColumn, ...columns] : columns));

function rowKey(row: any) {
  return String(row?.id || '');
}

/** 单条走 DELETE，多条走批量归档接口，与订单/售后口径一致 */
async function archiveShipments(ids: (string | number)[]) {
  const targets = Array.from(new Set(ids.map(id => String(id || '')).filter(Boolean)));
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res =
      targets.length === 1
        ? await del(`/api/admin/v1/shipments/${encodeURIComponent(targets[0])}`)
        : await post('/api/admin/v1/shipments/archive', { shipment_ids: targets });
    const data: any = res.data || {};
    const archived = Number(data.archived || 0);
    const skipped = Number(data.skipped || 0);
    const missing: string[] = data.missing || [];
    if (!archived && !skipped && !missing.length) window.$message?.info('没有可归档的运单');
    if (archived) window.$message?.success(`已归档 ${archived} 条运单`);
    if (skipped) window.$message?.info(`${skipped} 条运单此前已归档`);
    if (missing.length) window.$message?.warning(`${missing.length} 条运单不存在，已跳过`);
    checkedKeys.value = [];
    await fetch();
  } catch (e: any) {
    window.$message?.error(e?.response?.data?.message || '归档失败');
  } finally {
    archiving.value = false;
  }
}

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value };
    if (statusFilter.value) params.status = statusFilter.value;
    if (keyword.value.trim()) params.keyword = keyword.value.trim();
    const res = await get('/api/admin/v1/shipments/', params);
    const data: any = res.data || {};
    shipments.value = data.items || (Array.isArray(data) ? data : []);
    total.value = Number(data.total ?? shipments.value.length);
  } finally {
    loading.value = false;
  }
}

function searchNow() {
  page.value = 1;
  fetch();
}

function openModal(s?: any) {
  editing.value = s || null;
  form.value = s
    ? {
        order_id: s.order_id,
        carrier: s.carrier || '',
        tracking_number: s.tracking_number || '',
        status: s.status,
        estimated_delivery: s.estimated_delivery?.slice(0, 16) || '',
        origin: s.origin || '',
        destination: s.destination || ''
      }
    : {
        order_id: '',
        carrier: '',
        tracking_number: '',
        status: 'PENDING',
        estimated_delivery: '',
        origin: '',
        destination: ''
      };
  modalError.value = '';
  showModal.value = true;
}

async function save() {
  modalLoading.value = true;
  try {
    if (editing.value) {
      await patch(`/api/admin/v1/shipments/${editing.value.id}`, {
        tracking_number: form.value.tracking_number,
        status: form.value.status,
        estimated_delivery: form.value.estimated_delivery,
        carrier: form.value.carrier,
        origin: form.value.origin,
        destination: form.value.destination
      });
    } else {
      await post('/api/admin/v1/shipments/', form.value);
    }
    showModal.value = false;
    fetch();
  } catch (e: any) {
    modalError.value = e.response?.data?.detail || 'Save failed';
  } finally {
    modalLoading.value = false;
  }
}

onMounted(fetch);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center gap-3 flex-wrap">
      <NSpace>
        <NSelect
          v-model:value="statusFilter"
          :options="statusOptions"
          placeholder="全部状态"
          clearable
          style="width: 160px"
          @update:value="searchNow"
        />
        <NInput
          v-model:value="keyword"
          placeholder="运单号 / 承运商 / 订单号"
          style="width: 240px"
          clearable
          @keyup.enter="searchNow"
        />
      </NSpace>
      <NSpace align="center">
        <span class="text-sm text-[var(--n-text-color-3)]">{{ total }} shipment(s)</span>
        <NPopconfirm v-if="canArchive" @positive-click="archiveShipments(checkedKeys)">
          <template #trigger>
            <NButton type="error" secondary :disabled="!checkedKeys.length" :loading="archiving">
              批量删除{{ checkedKeys.length ? '（' + checkedKeys.length + '）' : '' }}
            </NButton>
          </template>
          确认删除所选 {{ checkedKeys.length }} 条运单？删除后不再出现在列表与看板，可恢复。
        </NPopconfirm>
        <NButton type="primary" @click="openModal()">{{ $t('common.add') }}</NButton>
      </NSpace>
    </div>

    <NDataTable
      v-model:checked-row-keys="checkedKeys"
      :row-key="rowKey"
      :columns="tableColumns"
      :data="shipments"
      :loading="loading"
      :bordered="false"
      size="small"
      :pagination="{
        page,
        pageSize,
        itemCount: total,
        pageSizes: [20, 50, 100],
        showSizePicker: true,
        onChange: (p: number) => {
          page = p;
          fetch();
        },
        onUpdatePageSize: (s: number) => {
          pageSize = s;
          page = 1;
          fetch();
        }
      }"
      remote
    />

    <NModal
      v-model:show="showModal"
      preset="card"
      :title="editing ? $t('common.edit') : $t('common.add')"
      style="width: 520px"
    >
      <NForm :model="form" label-placement="left" label-width="140">
        <NFormItem :label="$t('page.shipments.orderId')" :required="!editing">
          <NInput v-model:value="form.order_id" :disabled="!!editing" />
        </NFormItem>
        <NFormItem :label="$t('page.shipments.carrier')"><NInput v-model:value="form.carrier" /></NFormItem>
        <NFormItem :label="$t('page.shipments.trackingNumber')">
          <NInput v-model:value="form.tracking_number" />
        </NFormItem>
        <NFormItem :label="$t('common.status')">
          <NSelect v-model:value="form.status" :options="statusOptions" />
        </NFormItem>
        <NFormItem :label="$t('page.shipments.estimatedDelivery')">
          <NInput v-model:value="form.estimated_delivery" placeholder="2026-07-01T00:00:00" />
        </NFormItem>
        <NFormItem :label="$t('common.origin')"><NInput v-model:value="form.origin" /></NFormItem>
        <NFormItem :label="$t('common.destination')"><NInput v-model:value="form.destination" /></NFormItem>
      </NForm>
      <div v-if="modalError" class="text-red-500 text-sm mt-2">{{ modalError }}</div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showModal = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="modalLoading" @click="save">{{ $t('common.save') }}</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
