<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <span class="text-sm text-[var(--n-text-color-3)]">{{ shipments.length }} shipment(s)</span>
      <NButton type="primary" @click="openModal()">{{ $t('common.add') }}</NButton>
    </div>

    <NDataTable :columns="columns" :data="shipments" :loading="loading" :bordered="false" size="small" />

    <NModal v-model:show="showModal" preset="card" :title="editing ? $t('common.edit') : $t('common.add')" style="width:520px">
      <NForm :model="form" label-placement="left" label-width="140">
        <NFormItem :label="$t('page.shipments.orderId')" :required="!editing">
          <NInput v-model:value="form.order_id" :disabled="!!editing" />
        </NFormItem>
        <NFormItem :label="$t('page.shipments.carrier')"><NInput v-model:value="form.carrier" /></NFormItem>
        <NFormItem :label="$t('page.shipments.trackingNumber')"><NInput v-model:value="form.tracking_number" /></NFormItem>
        <NFormItem :label="$t('common.status')">
          <NSelect v-model:value="form.status" :options="statusOptions" />
        </NFormItem>
        <NFormItem :label="$t('page.shipments.estimatedDelivery')"><NInput v-model:value="form.estimated_delivery" placeholder="2026-07-01T00:00:00" /></NFormItem>
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

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, onMounted, h } from 'vue';
import { NButton, NDataTable, NInput, NModal, NForm, NFormItem, NSelect, NSpace, NTag } from 'naive-ui';
import { get, post, patch } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const shipments = ref<any[]>([]);
const showModal = ref(false);
const editing = ref<any>(null);
const modalError = ref('');
const modalLoading = ref(false);

const statusOptions = [
  { label: 'PENDING', value: 'PENDING' },
  { label: 'IN TRANSIT', value: 'IN_TRANSIT' },
  { label: 'DELIVERED', value: 'DELIVERED' },
  { label: 'FAILED', value: 'FAILED' },
];

const { t } = useI18n();
const form = ref({
  order_id: '', carrier: '', tracking_number: '',
  status: 'PENDING', estimated_delivery: '', origin: '', destination: '',
});

function formatDate(s: string) { return s ? new Date(s).toLocaleDateString() : '-'; }

const columns: DataTableColumns<any> = [
  { title: t('page.orders.orderNumber'), key: 'id', render: row => (row.id || '').slice(0, 8) },
  { title: t('page.shipments.orderId'), key: 'order_id', render: row => (row.order_id || '').slice(0, 8) },
  { title: t('page.shipments.carrier'), key: 'carrier' },
  { title: t('page.shipments.trackingNumber'), key: 'tracking_number' },
  {
    title: t('common.status'), key: 'status',
    render: row => h(NTag, { type: row.status === 'DELIVERED' ? 'success' : row.status === 'FAILED' ? 'error' : 'warning', size: 'small' }, { default: () => row.status }),
  },
  { title: t('page.shipments.estimatedDelivery'), key: 'estimated_delivery', render: row => formatDate(row.estimated_delivery) },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NButton, { size: 'small', onClick: () => openModal(row) }, { default: () => t('common.edit') }),
  },
];

async function fetch() {
  loading.value = true;
  try {
    const res = await get('/api/admin/v1/shipments/');
    shipments.value = res.data?.items || res.data || [];
  } finally { loading.value = false; }
}

function openModal(s?: any) {
  editing.value = s || null;
  form.value = s
    ? { order_id: s.order_id, carrier: s.carrier || '', tracking_number: s.tracking_number || '', status: s.status, estimated_delivery: s.estimated_delivery?.slice(0, 16) || '', origin: s.origin || '', destination: s.destination || '' }
    : { order_id: '', carrier: '', tracking_number: '', status: 'PENDING', estimated_delivery: '', origin: '', destination: '' };
  modalError.value = '';
  showModal.value = true;
}

async function save() {
  modalLoading.value = true;
  try {
    if (editing.value) {
      await patch(`/api/admin/v1/shipments/${editing.value.id}`, {
        tracking_number: form.value.tracking_number, status: form.value.status,
        estimated_delivery: form.value.estimated_delivery, carrier: form.value.carrier,
        origin: form.value.origin, destination: form.value.destination,
      });
    } else {
      await post('/api/admin/v1/shipments/', form.value);
    }
    showModal.value = false;
    fetch();
  } catch (e: any) {
    modalError.value = e.response?.data?.detail || 'Save failed';
  } finally { modalLoading.value = false; }
}

onMounted(fetch);
</script>
