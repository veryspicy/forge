<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, onMounted, h } from 'vue';
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
  NRadio
} from 'naive-ui';
import { get, post } from '@/service/api/helper';
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

const statusLabels: Record<string, string> = {
  requested: '待审核',
  approved: '待收货',
  received: '待退款',
  refunded: '已退款',
  rejected: '已驳回',
  cancelled: '已撤销',
  closed: '已关闭'
};

const statusTagTypes: Record<string, 'default' | 'warning' | 'info' | 'success' | 'error'> = {
  requested: 'warning',
  approved: 'info',
  received: 'info',
  refunded: 'success',
  rejected: 'error',
  cancelled: 'default',
  closed: 'default'
};

const statusOptions = [
  { label: t('page.returns.allStatus'), value: '' },
  ...Object.entries(statusLabels).map(([value, label]) => ({ label, value }))
];

function money(v: any) {
  return `$${Number(v ?? 0).toFixed(2)}`;
}

function fmt(s?: string) {
  return s ? new Date(s).toLocaleString() : '-';
}

/* ------------------------------- 列表 ------------------------------- */

async function fetchList() {
  loading.value = true;
  try {
    const res = await get('/api/admin/v1/returns/', {
      page: page.value,
      page_size: pageSize.value,
      status: status.value || undefined,
      keyword: keyword.value || undefined
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

const columns: DataTableColumns<any> = [
  { title: t('page.returns.returnNumber'), key: 'return_number', width: 170 },
  { title: t('page.returns.orderNumber'), key: 'order_number', width: 160 },
  {
    title: t('page.returns.status'),
    key: 'status',
    width: 110,
    render: row =>
      h(
        NTag,
        { type: statusTagTypes[row.status] || 'default', size: 'small' },
        { default: () => statusLabels[row.status] || row.status }
      )
  },
  { title: t('page.returns.refundAmount'), key: 'refund_amount', width: 110, render: row => money(row.refund_amount) },
  { title: t('page.returns.reason'), key: 'reason', render: row => returnReasonLabel(row.reason, t) },
  { title: t('page.returns.requestedAt'), key: 'requested_at', width: 165, render: row => fmt(row.requested_at) },
  { title: t('page.returns.deadline'), key: 'deadline_at', width: 165, render: row => fmt(row.deadline_at) },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render: row =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', onClick: () => openDetail(row) }, { default: () => t('page.returns.detail') }),
          h(
            NButton,
            { size: 'tiny', quaternary: true, type: 'primary', onClick: () => goOrder(row) },
            { default: () => t('page.returns.openOrder') }
          ),
          row.status === 'requested'
            ? h(
                NButton,
                { size: 'tiny', type: 'primary', onClick: () => openReview(row) },
                { default: () => t('page.returns.review') }
              )
            : null,
          row.status === 'approved'
            ? h(NButton, { size: 'tiny', onClick: () => doReceive(row) }, { default: () => t('page.returns.receive') })
            : null,
          row.status === 'received'
            ? h(
                NButton,
                { size: 'tiny', type: 'primary', onClick: () => openRefund(row) },
                { default: () => t('page.returns.refund') }
              )
            : null,
          row.status === 'requested' || row.status === 'approved' || row.status === 'received'
            ? h(NButton, { size: 'tiny', onClick: () => doClose(row) }, { default: () => t('page.returns.close') })
            : null
        ].filter(Boolean)
      })
  }
];

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
    window.$message?.error(e.response?.data?.message || 'Refund failed');
  } finally {
    submitting.value = false;
  }
}

function doReceive(row: any) {
  window.$dialog?.warning({
    title: t('page.returns.receive'),
    content: `${row.return_number}：确认已收到回寄商品？`,
    positiveText: '确定',
    negativeText: '取消',
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
    content: `${row.return_number}：关闭后该售后申请将终止，确定关闭？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      await post(`/api/admin/v1/returns/${row.return_number}/close`, { reason: 'closed by admin' });
      window.$message?.success(t('page.returns.actionDone'));
      refresh();
    }
  });
}

const itemColumns: DataTableColumns<any> = [
  { title: '商品', key: 'name', render: row => row.name || '-' },
  { title: 'SKU', key: 'sku', render: row => row.sku || '-' },
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
      <NTag v-for="(label, key) in statusLabels" :key="key" size="small" :bordered="false">
        {{ label }}：{{ stats[key] ?? 0 }}
      </NTag>
      <span class="text-sm text-[var(--n-text-color-3)]">
        {{ t('page.returns.refundAmount') }}：{{ money(stats.refunded_amount ?? 0) }}
      </span>
    </div>

    <div class="flex justify-between items-center gap-3 flex-wrap">
      <NSpace>
        <NSelect v-model:value="status" :options="statusOptions" style="width: 160px" @update:value="refresh" />
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
      <span class="text-sm text-[var(--n-text-color-3)]">{{ total }} {{ t('page.returns.list') }}</span>
    </div>

    <NDataTable
      :columns="columns"
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
        <NFormItem v-if="reviewForm.approved" label="入库">
          <NCheckbox v-model:checked="reviewForm.restock">商品回库</NCheckbox>
        </NFormItem>
        <NFormItem v-if="reviewForm.approved" label="运费">
          <NCheckbox v-model:checked="reviewForm.refund_shipping">退运费</NCheckbox>
        </NFormItem>
        <NFormItem :label="reviewForm.approved ? t('page.returns.reviewNote') : t('page.returns.reviewNote') + ' *'">
          <NInput v-model:value="reviewForm.note" type="textarea" :rows="3" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showReview = false">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="submitReview">提交</NButton>
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
          <NButton @click="showRefund = false">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="submitRefund">执行退款</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
