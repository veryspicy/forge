<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <NSelect
        v-model:value="adoptedFilter"
        :options="filterOptions"
        :placeholder="$t('common.adopted')"
        clearable
        style="width:150px"
        @update:value="fetch"
      />
    </div>

    <NDataTable :columns="columns" :data="conversations" :loading="loading" :bordered="false" size="small" />

    <div v-if="total > pageSize" class="flex justify-center">
      <NPagination :page="page" :page-size="pageSize" :item-count="total" @update:page="goPage" />
    </div>

    <NModal :show="!!detailConv" preset="card" :title="$t('common.conversation')" style="width:640px" @update:show="(v) => { if (!v) detailConv = null; }">
      <div class="flex flex-col gap-3">
        <div><span class="text-[var(--n-text-color-3)]">User ID: </span>{{ detailConv?.user_id }}</div>
        <div><span class="text-[var(--n-text-color-3)]">Product: </span>{{ detailConv?.product_name || '-' }}</div>
        <div><span class="text-[var(--n-text-color-3)]">Adopted: </span>{{ detailConv?.is_adopted ? t('common.yes') : t('common.no') }}</div>
        <div><span class="text-[var(--n-text-color-3)]">Started: </span>{{ detailConv?.created_at }}</div>
        <NDivider />
        <h4 class="text-sm font-semibold">{{ $t('common.messages') }}</h4>
        <div v-if="detailConv?.messages?.length" class="max-h-[300px] overflow-y-auto bg-[var(--n-color-embedded)] rounded-md p-3 text-sm">
          <div v-for="(m, i) in detailConv.messages" :key="i" class="py-1.5 border-b border-[var(--n-divider-color)] last:border-b-0">
            <span class="font-semibold" :style="{ color: m.role === 'user' ? 'var(--n-color-target)' : '#27ae60' }">{{ m.role }}</span>: {{ m.content?.slice(0, 300) }}
          </div>
        </div>
        <div v-else class="text-[var(--n-text-color-3)] py-3">{{ $t('page.aiProbe.noMessages') }}</div>
      </div>
      <template #footer>
        <NButton @click="detailConv = null">{{ $t('common.close') }}</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted, h } from 'vue';
import { NButton, NDataTable, NDivider, NModal, NPagination, NSelect, NTag } from 'naive-ui';
import { get } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const loading = ref(false);
const conversations = ref<any[]>([]);
const adoptedFilter = ref<string | null>(null);
const page = ref(1);
const total = ref(0);
const { t } = useI18n();
const pageSize = 20;
const detailConv = ref<any>(null);

const filterOptions = [
  { label: t('common.adopted'), value: 'true' },
  { label: t('common.notAdopted'), value: 'false' },
];

const columns: DataTableColumns<any> = [
  { title: t('common.conversation') + ' ID', key: 'conversation_id', render: row => (row.conversation_id || row.id || '').slice(0, 12) + '...' },
  { title: t('common.userId'), key: 'user_id', render: row => (row.user_id || '').slice(0, 8) + '...' },
  { title: t('common.product'), key: 'product_name', render: row => row.product_name || '-' },
  { title: t('common.messages'), key: 'message_count', render: row => row.message_count ?? 0 },
  {
    title: t('common.adopted'), key: 'is_adopted',
    render: row => h(NTag, { type: row.is_adopted ? 'success' : 'default', size: 'small' }, { default: () => row.is_adopted ? t('common.yes') : t('common.no') }),
  },
  { title: t('common.started'), key: 'created_at', render: row => row.created_at ? new Date(row.created_at).toLocaleString() : '-' },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NButton, { size: 'small', onClick: () => openDetail(row) }, { default: () => t('common.view') }),
  },
];

async function fetch() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize };
    if (adoptedFilter.value !== null) params.adopted = adoptedFilter.value === 'true';
    const res = await get('/api/admin/v1/chat-requests/', { params });
    conversations.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally { loading.value = false; }
}

function goPage(p: number) { page.value = p; fetch(); }

async function openDetail(c: any) {
  try {
    const res = await get(`/api/admin/v1/chat-requests/${c.conversation_id || c.id}`);
    detailConv.value = res.data;
  } catch (e) { console.error(e); }
}

onMounted(fetch);
</script>
