<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted, h, resolveComponent } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import {
  NButton,
  NDataTable,
  NInput,
  NInputNumber,
  NModal,
  NForm,
  NFormItem,
  NSelect,
  NSpace,
  NTag,
  NDrawer,
  NDrawerContent,
  NCheckbox,
  NDescriptions,
  NDescriptionsItem,
  NRadioGroup,
  NRadio,
  NPopconfirm
} from 'naive-ui';
import { get, post, del } from '@/service/api/helper';
import { useAuthStore } from '@/store/modules/auth';
import { returnReasonLabel } from '@/constants/aftersalesReasons';
import type { DataTableColumns } from 'naive-ui';

const { t } = useI18n();

const loading = ref(false);
const rows = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const status = ref<string | null>(null);
const keyword = ref('');
const stats = ref<Record<string, number>>({});

/** 售后状态文案（随语言切换） */
const statusLabels = computed<Record<string, string>>(() => ({
  requested: t('page.returns.statusRequested'),
  approved: t('page.returns.statusApproved'),
  received: t('page.returns.statusReceived'),
  refunded: t('page.returns.statusRefunded'),
  rejected: t('page.returns.statusRejected'),
  cancelled: t('page.returns.statusCancelled'),
  closed: t('page.returns.statusClosed')
}));

const statusTagTypes: Record<string, 'default' | 'warning' | 'info' | 'success' | 'error'> = {
  requested: 'warning',
  approved: 'info',
  received: 'warning',
  refunded: 'success',
  rejected: 'error',
  cancelled: 'default',
  closed: 'default'
};

/** 状态语义图标：审核中/待收货/待退款/已退款/已驳回/已撤销/已关闭 */
const statusIcons: Record<string, string> = {
  requested: 'mdi:clipboard-clock-outline',
  approved: 'mdi:package-variant-closed',
  received: 'mdi:cash-clock',
  refunded: 'mdi:cash-check',
  rejected: 'mdi:close-octagon-outline',
  cancelled: 'mdi:undo-variant',
  closed: 'mdi:lock-outline'
};

function statusIcon(state: string) {
  return statusIcons[state] || 'mdi:help-circle-outline';
}

const statusOptions = computed(() => [
  { label: t('page.returns.allStatus'), value: '' },
  ...Object.entries(statusLabels.value).map(([value, label]) => ({ label, value }))
]);

function money(v: any) {
  return `$${Number(v ?? 0).toFixed(2)}`;
}

function fmt(s?: string) {
  return s ? new Date(s).toLocaleString() : '-';
}

/* ------------------------------- 列表 ------------------------------- */

/** 列表视图：默认仅看进行中记录；切到「已归档」时列出 admin_archived_at 已置位的记录 */
const archivedView = ref(false);
/** NSelect 仅接受字符串值，这里做布尔语义到字符串视图的映射 */
const viewValue = computed(() => (archivedView.value ? 'archived' : 'active'));
const viewOptions = computed(() => [
  { label: t('page.archive.viewActive'), value: 'active' },
  { label: t('page.archive.viewArchived'), value: 'archived' }
]);

async function fetchList() {
  loading.value = true;
  try {
    const res = await get('/api/admin/v1/returns/', {
      page: page.value,
      page_size: pageSize.value,
      status: status.value || undefined,
      keyword: keyword.value || undefined,
      archived: archivedView.value || undefined
    });
    rows.value = res.data?.items || [];
    total.value = res.data?.total ?? rows.value.length;
  } finally {
    loading.value = false;
  }
}

async function fetchStats() {
  const res = await get('/api/admin/v1/returns/stats');
  stats.value = res.data || {};
}

function refresh() {
  fetchList();
  fetchStats();
}

const route = useRoute();
const router = useRouter();

const debouncedFetchList = useDebounceFn(() => {
  page.value = 1;
  refresh();
}, 400);

/** 立即查询：清空关键词 / 回车 / 切换状态时调用，取消防抖中挂起的请求 */
function searchNow() {
  (debouncedFetchList as any).cancel?.();
  page.value = 1;
  refresh();
}

/**
 * 输入即触发：停止输入 400ms 自动查询；清空关键词立即回到全量。
 * 通过 NInput 的 @update:value 直接驱动，避免依赖 watch 时序。
 */
function onKeywordInput(value: string | null) {
  if (!String(value ?? '').trim()) searchNow();
  else debouncedFetchList();
}

function goOrder(row: any) {
  if (row?.order_number) router.push(`/orders/${row.order_number}`);
}

const authStore = useAuthStore();

/** 归档（后台删除）入口仅对持有 orders:archive 的角色渲染；super_admin 走权限通配 '*' */
const canArchive = computed(() => {
  const perms = authStore.userInfo.permissions || [];
  return perms.includes('*') || perms.includes('orders:archive');
});

/** 归档/恢复选中项；行级操作复用同一套请求逻辑（单条走 DELETE，多条走批量接口） */
const checkedKeys = ref<string[]>([]);

function switchView(value: string) {
  archivedView.value = value === 'archived';
  checkedKeys.value = [];
  page.value = 1;
  refresh();
}

const archiving = ref(false);

function uniq(list: (string | number)[]) {
  return Array.from(new Set(list.map(v => String(v ?? '')).filter(Boolean)));
}

/** 归档/恢复结果统一提示（后端返回 archived|restored / skipped / missing） */
function notifyArchiveResult(data: any, mode: 'archive' | 'restore') {
  const target = t('page.archive.targetReturn');
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

/** 单条走 DELETE，多条走批量归档接口，与订单页口径一致 */
async function archiveReturns(returnNumbers: string[]) {
  const targets = uniq(returnNumbers);
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res =
      targets.length === 1
        ? await del(`/api/admin/v1/returns/${encodeURIComponent(targets[0])}`)
        : await post('/api/admin/v1/returns/archive', { return_numbers: targets });
    notifyArchiveResult(res.data || {}, 'archive');
    checkedKeys.value = [];
    refresh();
  } catch (e: any) {
    window.$message?.error(e?.response?.data?.message || t('page.archive.failed'));
  } finally {
    archiving.value = false;
  }
}

/** 恢复已归档售后单；批量接口幂等，未归档的会被 skipped */
async function restoreReturns(returnNumbers: string[]) {
  const targets = uniq(returnNumbers);
  if (!targets.length) return;
  archiving.value = true;
  try {
    const res = await post('/api/admin/v1/returns/unarchive', { return_numbers: targets });
    notifyArchiveResult(res.data || {}, 'restore');
    checkedKeys.value = [];
    refresh();
  } catch (e: any) {
    window.$message?.error(e?.response?.data?.message || t('page.archive.restoreFailed'));
  } finally {
    archiving.value = false;
  }
}

const columns: DataTableColumns<any> = [
  { title: t('page.returns.returnNumber'), key: 'return_number', width: 170 },
  { title: t('page.returns.orderNumber'), key: 'order_number', width: 160 },
  {
    title: t('page.returns.status'),
    key: 'status',
    width: 130,
    render: row => {
      const Icon = resolveComponent('SvgIcon');
      return h(
        NTag,
        { type: statusTagTypes[row.status] || 'default', size: 'small' },
        {
          icon: () => h(Icon, { icon: statusIcon(row.status) }),
          default: () => statusLabels.value[row.status] || row.status
        }
      );
    }
  },
  { title: t('page.returns.refundAmount'), key: 'refund_amount', width: 110, render: row => money(row.refund_amount) },
  { title: t('page.returns.reason'), key: 'reason', render: row => returnReasonLabel(row.reason, t) },
  { title: t('page.returns.requestedAt'), key: 'requested_at', width: 165, render: row => fmt(row.requested_at) },
  { title: t('page.returns.deadline'), key: 'deadline_at', width: 165, render: row => fmt(row.deadline_at) },
  {
    title: t('common.action'),
    key: 'actions',
    width: 300,
    render: row =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', onClick: () => openDetail(row) }, { default: () => t('page.returns.detail') }),
          h(
            NButton,
            { size: 'tiny', quaternary: true, type: 'primary', onClick: () => goOrder(row) },
            { default: () => t('page.returns.openOrder') }
          ),
          // 已归档记录只保留查看与恢复入口，不再展示推进流程的操作
          !archivedView.value && row.status === 'requested'
            ? h(
                NButton,
                { size: 'tiny', type: 'primary', onClick: () => openReview(row) },
                { default: () => t('page.returns.review') }
              )
            : null,
          !archivedView.value && row.status === 'approved'
            ? h(NButton, { size: 'tiny', onClick: () => doReceive(row) }, { default: () => t('page.returns.receive') })
            : null,
          !archivedView.value && row.status === 'received'
            ? h(
                NButton,
                { size: 'tiny', type: 'primary', onClick: () => openRefund(row) },
                { default: () => t('page.returns.refund') }
              )
            : null,
          !archivedView.value && ['requested', 'approved', 'received'].includes(row.status)
            ? h(NButton, { size: 'tiny', onClick: () => doClose(row) }, { default: () => t('page.returns.close') })
            : null,
          canArchive.value
            ? h(
                NPopconfirm,
                {
                  onPositiveClick: () =>
                    archivedView.value ? restoreReturns([row.return_number]) : archiveReturns([row.return_number])
                },
                {
                  trigger: () =>
                    h(
                      NButton,
                      { size: 'tiny', quaternary: true, type: archivedView.value ? 'primary' : 'error' },
                      { default: () => t(archivedView.value ? 'page.archive.restore' : 'page.archive.action') }
                    ),
                  default: () =>
                    t(archivedView.value ? 'page.archive.restoreConfirm' : 'page.archive.confirm', {
                      target: t('page.archive.targetReturn')
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
  disabled: (row: any) => !row.return_number
};

const tableColumns = computed<DataTableColumns<any>>(() =>
  canArchive.value ? [selectionColumn, ...columns] : columns
);

function rowKey(row: any) {
  return String(row?.return_number || '');
}

/* ------------------------------- 详情 ------------------------------- */

const showDetail = ref(false);
const current = ref<any>(null);

function openDetail(row: any) {
  current.value = row;
  showDetail.value = true;
}

/* ------------------------------- 审核 ------------------------------- */

const showReview = ref(false);
const reviewRow = ref<any>(null);
const reviewForm = ref({ approved: true, note: '', restock: true, refund_shipping: false, deadline_days: 14 });
const submitting = ref(false);

function openReview(row: any) {
  reviewRow.value = row;
  reviewForm.value = { approved: true, note: '', restock: true, refund_shipping: false, deadline_days: 14 };
  showReview.value = true;
}

async function submitReview() {
  if (!reviewForm.value.approved && !reviewForm.value.note.trim()) {
    window.$message?.error(t('page.returns.rejectNoteRequired'));
    return;
  }
  submitting.value = true;
  try {
    await post(`/api/admin/v1/returns/${reviewRow.value.return_number}/review`, reviewForm.value);
    window.$message?.success(t('page.returns.actionDone'));
    showReview.value = false;
    refresh();
  } catch (e: any) {
    window.$message?.error(e.response?.data?.message || 'Review failed');
  } finally {
    submitting.value = false;
  }
}

/* ------------------------------- 收货 / 退款 / 关闭 ------------------------------- */

const showRefund = ref(false);
const refundRow = ref<any>(null);
const refundNote = ref('');

function openRefund(row: any) {
  refundRow.value = row;
  refundNote.value = '';
  showRefund.value = true;
}

async function submitRefund() {
  submitting.value = true;
  try {
    await post(`/api/admin/v1/returns/${refundRow.value.return_number}/refund`, { note: refundNote.value || null });
    window.$message?.success(t('page.returns.actionDone'));
    showRefund.value = false;
    refresh();
  } catch (e: any) {
    window.$message?.error(e.response?.data?.message || t('page.returns.refundFailed'));
  } finally {
    submitting.value = false;
  }
}

function doReceive(row: any) {
  window.$dialog?.warning({
    title: t('page.returns.receive'),
    content: t('page.returns.receiveConfirm', { no: row.return_number }),
    positiveText: t('common.confirm'),
    negativeText: t('common.cancel'),
    onPositiveClick: async () => {
      await post(`/api/admin/v1/returns/${row.return_number}/receive`, {});
      window.$message?.success(t('page.returns.actionDone'));
      refresh();
    }
  });
}

function doClose(row: any) {
  window.$dialog?.warning({
    title: t('page.returns.close'),
    content: t('page.returns.closeConfirm', { no: row.return_number }),
    positiveText: t('common.confirm'),
    negativeText: t('common.cancel'),
    onPositiveClick: async () => {
      await post(`/api/admin/v1/returns/${row.return_number}/close`, { reason: 'closed by admin' });
      window.$message?.success(t('page.returns.actionDone'));
      refresh();
    }
  });
}

const itemColumns: DataTableColumns<any> = [
  { title: t('page.returns.itemName'), key: 'name', render: row => row.name || '-' },
  { title: t('common.sku'), key: 'sku', render: row => row.sku || '-' },
  { title: t('page.returns.unitPrice'), key: 'unit_price', render: row => money(row.unit_price) },
  { title: t('page.returns.quantity'), key: 'quantity' }
];

onMounted(() => {
  // 由订单列表跳转进来时带 keyword（订单号），自动定位该订单的售后单
  const q = route.query.keyword;
  if (typeof q === 'string' && q.trim()) {
    keyword.value = q.trim();
  }
  refresh();
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3 flex-wrap">
      <NTag
        v-for="(label, key) in statusLabels"
        :key="key"
        size="small"
        :type="statusTagTypes[key] || 'default'"
        :bordered="false"
      >
        <template #icon>
          <SvgIcon :icon="statusIcon(key)" />
        </template>
        {{ label }}：{{ stats[key] ?? 0 }}
      </NTag>
      <span class="text-sm text-[var(--n-text-color-3)]">
        {{ t('page.returns.refundAmount') }}：{{ money(stats.refunded_amount ?? 0) }}
      </span>
    </div>

    <div class="flex justify-between items-center gap-3 flex-wrap">
      <NSpace>
        <NSelect v-model:value="status" :options="statusOptions" style="width: 160px" @update:value="refresh" />
        <NSelect :value="viewValue" :options="viewOptions" style="width: 140px" @update:value="switchView" />
        <NInput
          v-model:value="keyword"
          :placeholder="t('page.returns.searchPlaceholder')"
          style="width: 280px"
          clearable
          :input-props="{ autocomplete: 'off' }"
          @update:value="onKeywordInput"
          @keyup.enter="searchNow"
        />
      </NSpace>
      <NPopconfirm
        v-if="canArchive"
        @positive-click="archivedView ? restoreReturns(checkedKeys) : archiveReturns(checkedKeys)"
      >
        <template #trigger>
          <NButton
            :type="archivedView ? 'primary' : 'error'"
            secondary
            :disabled="!checkedKeys.length"
            :loading="archiving"
          >
            {{ archivedView ? t('page.archive.restoreBatch') : t('page.archive.actionBatch')
            }}{{ checkedKeys.length ? ' (' + checkedKeys.length + ')' : '' }}
          </NButton>
        </template>
        {{
          archivedView
            ? t('page.archive.restoreConfirmBatch', { n: checkedKeys.length, target: t('page.archive.targetReturn') })
            : t('page.archive.confirmBatch', { n: checkedKeys.length, target: t('page.archive.targetReturn') })
        }}
      </NPopconfirm>
      <span class="text-sm text-[var(--n-text-color-3)]">{{ total }} {{ t('page.returns.list') }}</span>
    </div>

    <NDataTable
      v-model:checked-row-keys="checkedKeys"
      :row-key="rowKey"
      :columns="tableColumns"
      :data="rows"
      :loading="loading"
      :bordered="false"
      size="small"
      :pagination="{
        page: page,
        pageSize: pageSize,
        itemCount: total,
        showSizePicker: true,
        pageSizes: [20, 50, 100],
        onChange: (p: number) => {
          page = p;
          fetchList();
        },
        onUpdatePageSize: (s: number) => {
          pageSize = s;
          page = 1;
          fetchList();
        }
      }"
      remote
    />

    <!-- 详情抽屉 -->
    <NDrawer v-model:show="showDetail" :width="560">
      <NDrawerContent :title="t('page.returns.detail')" closable>
        <NDescriptions v-if="current" :column="1" label-placement="left" bordered size="small">
          <NDescriptionsItem :label="t('page.returns.returnNumber')">{{ current.return_number }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.orderNumber')">{{ current.order_number || '-' }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.status')">
            {{ statusLabels[current.status] || current.status }}
          </NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.reason')">{{ returnReasonLabel(current.reason, t) }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.refundAmount')">{{ money(current.refund_amount) }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.refundMethod')">{{ current.refund_method || '-' }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.requestedAt')">{{ fmt(current.requested_at) }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.deadline')">{{ fmt(current.deadline_at) }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.carrier')">{{ current.carrier || '-' }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.trackingNumber')">
            {{ current.tracking_number || '-' }}
          </NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.shippedAt')">{{ fmt(current.shipped_at) }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.reviewNote')">{{ current.review_note || '-' }}</NDescriptionsItem>
          <NDescriptionsItem :label="t('page.returns.note')">{{ current.note || '-' }}</NDescriptionsItem>
        </NDescriptions>
        <div class="mt-4 flex justify-end">
          <NButton size="small" secondary type="primary" :disabled="!current?.order_number" @click="goOrder(current)">
            {{ t('page.returns.openOrder') }}
          </NButton>
        </div>
        <div class="mt-4 text-sm font-medium">{{ t('page.returns.items') }}</div>
        <NDataTable
          class="mt-2"
          :columns="itemColumns"
          :data="current?.items || []"
          :bordered="false"
          size="small"
        />
      </NDrawerContent>
    </NDrawer>

    <!-- 审核弹窗 -->
    <NModal v-model:show="showReview" preset="card" :title="t('page.returns.review')" style="width: 520px">
      <NForm :model="reviewForm" label-placement="left" label-width="140">
        <NFormItem :label="t('page.returns.status')">
          <NRadioGroup v-model:value="reviewForm.approved">
            <NRadio :value="true">{{ t('page.returns.approve') }}</NRadio>
            <NRadio :value="false">{{ t('page.returns.reject') }}</NRadio>
          </NRadioGroup>
        </NFormItem>
        <NFormItem v-if="reviewForm.approved" :label="t('page.returns.deadlineDays')">
          <NInputNumber v-model:value="reviewForm.deadline_days" :min="1" :max="90" />
        </NFormItem>
        <NFormItem v-if="reviewForm.approved" :label="t('page.returns.restock')">
          <NCheckbox v-model:checked="reviewForm.restock">{{ t('page.returns.restockItem') }}</NCheckbox>
        </NFormItem>
        <NFormItem v-if="reviewForm.approved" :label="t('page.returns.shipping')">
          <NCheckbox v-model:checked="reviewForm.refund_shipping">{{ t('page.returns.refundShipping') }}</NCheckbox>
        </NFormItem>
        <NFormItem :label="reviewForm.approved ? t('page.returns.reviewNote') : t('page.returns.reviewNote') + ' *'">
          <NInput v-model:value="reviewForm.note" type="textarea" :rows="3" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showReview = false">{{ t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="submitting" @click="submitReview">{{ t('common.submit') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 退款弹窗 -->
    <NModal v-model:show="showRefund" preset="card" :title="t('page.returns.refund')" style="width: 480px">
      <div class="text-sm mb-3">
        {{ t('page.returns.refundAmount') }}：{{ money(refundRow?.refund_amount) }}
      </div>
      <NInput v-model:value="refundNote" type="textarea" :rows="3" :placeholder="t('page.returns.note')" />
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showRefund = false">{{ t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="submitting" @click="submitRefund">{{ t('page.returns.refundAction') }}</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
