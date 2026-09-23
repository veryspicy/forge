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

/** 列表视图：默认仅看进行中记录；切到「已归档」时列出 admin_archived_at 已置位的记录 */
const archivedView = ref(false);
const viewOptions = computed(() => [
  { label: t('page.archive.viewActive'), value: 'active' },
  { label: t('page.archive.viewArchived'), value: 'archived' }
]);
const viewValue = computed(() => (archivedView.value ? 'archived' : 'active'));

function switchView(value: string) {
  archivedView.value = value === 'archived';
  checkedKeys.value = [];
  page.value = 1;
  fetch();
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
                {
                  onPositiveClick: () =>
                    archivedView.value ? restoreShipments([row.id]) : archiveShipments([row.id])
                },
                {
                  trigger: () =>
                    h(
                      NButton,
                      { size: 'small', quaternary: true, type: archivedView.value ? 'primary' : 'error' },
                      { default: () => t(archivedView.value ? 'page.archive.restore' : 'page.archive.action') }
                    ),
                  default: () =>
                    t(archivedView.value ? 'page.archive.restoreConfirm' : 'page.archive.confirm', {
                      target: t('page.archive.targetShipment')
                    })
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

function uniq(list: (string | number)[]) {
  return Array.from(new Set(list.map(v => String(v ?? '')).filter(Boolean)));
}

/** 归档/恢复结果统一提示（后端返回 archived|restored / skipped / missing） */
function notifyArchiveResult(data: any, mode: 'archive' | 'restore') {
  const target = t('page.archive.targetShipment');
  const count = Number((mode === 'archive' ? data.archived : data.restored) || 0);
  const skipped = Number(data.skipped || 0);
  const missing: string[] = data.missing || [];
  const msg = (key: string, n: number) => t(`page.archive.${key}`, { n, target });
  if (!count && !skipped && !missing.length) {
    window.$message?.info(t(mode === 'archive' ? 'page.archive.empty' : 'page.archive.restoreEmpty', { target }));
  }
  if (count) window.$message?.success(msg(mode === 'archive' ? 'done' : 'restoreDone', count));
  if (skipped) window.$message?.info(msg(mode === 'archive' ? 'skipped' : 'restoreSkipped', skipped));
  if (missing.length) window.$message?.warning(msg(mode === 'archive' ? 'missing' : 'restoreMissing', missing.length));
}

/** 单条走 DELETE，多条走批量归档接口，与订单/售后口径一致 */
async function archiveShipments(ids: (string | number)[]) {
  const targets = uniq(ids);
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res =
      targets.length === 1
        ? await del(`/api/admin/v1/shipments/${encodeURIComponent(targets[0])}`)
        : await post('/api/admin/v1/shipments/archive', { shipment_ids: targets });
    notifyArchiveResult(res.data || {}, 'archive');
    checkedKeys.value = [];
    await fetch();
  } catch (e: any) {
    window.$message?.error(e?.response?.data?.message || t('page.archive.failed'));
  } finally {
    archiving.value = false;
  }
}

/** 恢复已归档运单；批量接口幂等，未归档的会被 skipped */
async function restoreShipments(ids: (string | number)[]) {
  const targets = uniq(ids);
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res = await post('/api/admin/v1/shipments/unarchive', { shipment_ids: targets });
    notifyArchiveResult(res.data || {}, 'restore');
    checkedKeys.value = [];
    await fetch();
  } catch (e: any) {
    window.$message?.error(e?.response?.data?.message || t('page.archive.restoreFailed'));
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
    if (archivedView.value) params.archived = true;
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
    modalError.value = e.response?.data?.detail || t('page.shipments.saveFailed');
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
          :placeholder="$t('page.shipments.statusAll')"
          clearable
          style="width: 160px"
          @update:value="searchNow"
        />
        <NSelect :value="viewValue" :options="viewOptions" style="width: 140px" @update:value="switchView" />
        <NInput
          v-model:value="keyword"
          :placeholder="$t('page.shipments.searchPlaceholder')"
          style="width: 240px"
          clearable
          @keyup.enter="searchNow"
        />
      </NSpace>
      <NSpace align="center">
        <span class="text-sm text-[var(--n-text-color-3)]">{{ $t('page.shipments.totalCount', { n: total }) }}</span>
        <NPopconfirm
          v-if="canArchive"
          @positive-click="archivedView ? restoreShipments(checkedKeys) : archiveShipments(checkedKeys)"
        >
          <template #trigger>
            <NButton
              :type="archivedView ? 'primary' : 'error'"
              secondary
              :disabled="!checkedKeys.length"
              :loading="archiving"
            >
              {{ archivedView ? $t('page.archive.restoreBatch') : $t('page.archive.actionBatch')
              }}{{ checkedKeys.length ? ' (' + checkedKeys.length + ')' : '' }}
            </NButton>
          </template>
          {{
            archivedView
              ? $t('page.archive.restoreConfirmBatch', {
                n: checkedKeys.length,
                target: $t('page.archive.targetShipment')
              })
              : $t('page.archive.confirmBatch', { n: checkedKeys.length, target: $t('page.archive.targetShipment') })
          }}
        </NPopconfirm>
        <NButton v-if="!archivedView" type="primary" @click="openModal()">{{ $t('common.add') }}</NButton>
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
