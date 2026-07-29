<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <NSpace>
        <NSelect
          v-model:value="activeFilter"
          :options="filterOptions"
          :placeholder="$t('page.suppliers.status')"
          clearable
          style="width:140px"
          @update:value="fetch"
        />
      </NSpace>
      <NButton type="primary" @click="openCreate">{{ $t('page.suppliers.addSupplier') }}</NButton>
    </div>

    <NDataTable
      :columns="columns"
      :data="suppliers"
      :loading="loading"
      :bordered="false"
      size="small"
    />

    <NModal v-model:show="showModal" preset="card" :title="editing ? $t('page.suppliers.editSupplier') : $t('page.suppliers.addSupplier')" style="width:520px">
      <NForm :model="form" label-placement="left" label-width="140">
        <NFormItem :label="$t('page.suppliers.name')" required><NInput v-model:value="form.name" /></NFormItem>
        <NFormItem :label="$t('page.suppliers.contactEmail')"><NInput v-model:value="form.contact_email" type="text" /></NFormItem>
        <NFormItem :label="$t('page.suppliers.contactPhone')"><NInput v-model:value="form.contact_phone" /></NFormItem>
        <NFormItem :label="$t('page.suppliers.integrationType')">
          <NSelect v-model:value="form.integration_type" :options="integrationOptions" />
        </NFormItem>
        <NFormItem :label="$t('page.suppliers.shippingRegions')">
          <NInput v-model:value="regionsString" placeholder="comma separated" @update:value="updateRegions" />
        </NFormItem>
        <NFormItem :label="$t('page.suppliers.defaultCurrency')"><NInput v-model:value="form.default_currency" /></NFormItem>
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
import { ref, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NDataTable, NInput, NModal, NForm, NFormItem, NSelect, NSpace, NTag } from 'naive-ui';
import { get, post, patch } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const suppliers = ref<any[]>([]);
const activeFilter = ref<string | null>(null);
const showModal = ref(false);
const editing = ref<any>(null);
const { t } = useI18n();
const modalError = ref('');
const modalLoading = ref(false);
const regionsString = ref('');

const filterOptions = [
  { label: t('page.suppliers.active'), value: 'true' },
  { label: t('page.suppliers.inactive'), value: 'false' },
];

const integrationOptions = [
  { label: 'Manual', value: 'manual' },
  { label: 'API', value: 'api' },
  { label: 'Dropship', value: 'dropship' },
];

const form = ref({
  name: '', contact_email: '', contact_phone: '',
  integration_type: 'manual', shipping_regions: [] as string[],
  default_currency: 'USD',
});

function updateRegions() {
  form.value.shipping_regions = regionsString.value.split(',').map(s => s.trim()).filter(Boolean);
}

const columns: DataTableColumns<any> = [
  { title: t('page.suppliers.name'), key: 'name' },
  { title: () => t('page.suppliers.contactEmail'), key: 'contact_email', render: row => row.contact_email || '-' },
  { title: t('page.suppliers.integrationType'), key: 'integration_type' },
  { title: t('page.suppliers.shippingRegions'), key: 'shipping_regions', render: row => (row.shipping_regions || []).join(', ') },
  {
    title: t('page.suppliers.active'), key: 'is_active',
    render: row => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? t('page.suppliers.active') : t('page.suppliers.inactive') }),
  },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEdit(row) }, { default: () => t('common.edit') }),
        row.is_active ? h(NButton, { size: 'small', type: 'warning', onClick: () => deactivate(row.id) }, { default: () => t('page.suppliers.inactive') }) : null,
      ],
    }),
  },
];

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = {};
    if (activeFilter.value !== null) params.is_active = activeFilter.value === 'true';
    const res = await get('/api/admin/v1/suppliers/', { params });
    suppliers.value = res.data?.items || res.data || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = { name: '', contact_email: '', contact_phone: '', integration_type: 'manual', shipping_regions: [], default_currency: 'USD' };
  regionsString.value = '';
  modalError.value = '';
  showModal.value = true;
}

function openEdit(s: any) {
  editing.value = s;
  form.value = {
    name: s.name, contact_email: s.contact_email || '', contact_phone: s.contact_phone || '',
    integration_type: s.integration_type || 'manual', shipping_regions: s.shipping_regions || [],
    default_currency: s.default_currency || 'USD',
  };
  regionsString.value = (s.shipping_regions || []).join(', ');
  modalError.value = '';
  showModal.value = true;
}

async function save() {
  modalLoading.value = true;
  modalError.value = '';
  try {
    if (editing.value) {
      await patch(`/api/admin/v1/suppliers/${editing.value.id}`, form.value);
    } else {
      await post('/api/admin/v1/suppliers/', form.value);
    }
    showModal.value = false;
    fetch();
  } catch (e: any) {
    modalError.value = e.response?.data?.detail || 'Save failed';
  } finally {
    modalLoading.value = false;
  }
}

async function deactivate(id: string) {
  try { await post(`/api/admin/v1/suppliers/${id}/deactivate`); fetch(); } catch (e) { console.error(e); }
}

onMounted(fetch);
</script>
