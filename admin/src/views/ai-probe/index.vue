<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NCard, NEmpty, NTag } from 'naive-ui';
import { get } from '@/service/api/helper';

interface ProbeItem {
  key: string;
  name: string;
  status: 'ok' | 'warn' | 'fail';
  latency_ms: number;
  detail: string;
}

interface ProbeResult {
  overall: 'ok' | 'warn' | 'fail';
  checked_at: string;
  items: ProbeItem[];
}

const { t } = useI18n();
const loading = ref(false);
const result = ref<ProbeResult | null>(null);

const overallTagType = computed(() => statusTagType(result.value?.overall ?? 'fail'));
const overallTagLabel = computed(() => statusLabel(result.value?.overall ?? 'fail'));

function statusTagType(status: string) {
  if (status === 'ok') return 'success';
  if (status === 'warn') return 'warning';
  return 'error';
}

function statusLabel(status: string) {
  if (status === 'ok') return 'statusOk';
  if (status === 'warn') return 'statusWarn';
  return 'statusFail';
}

function itemName(item: ProbeItem) {
  const map: Record<string, string> = {
    ai_service: t('page.aiProbe.aiService'),
    llm_key: t('page.aiProbe.llmKey'),
    database: t('page.aiProbe.database')
  };
  return map[item.key] ?? item.name;
}

async function fetchProbe() {
  loading.value = true;
  try {
    const res = await get('/api/admin/v1/ai/probe');
    result.value = res.data;
  } catch (e) {
    console.error(e);
    result.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchProbe);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold">{{ $t('page.aiProbe.aiProbeTitle') }}</h2>
        <NTag v-if="result" :type="overallTagType" size="small">
          {{ $t(`page.aiProbe.${overallTagLabel}`) }}
        </NTag>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="result" class="text-xs text-[var(--n-text-color-3)]">
          {{ $t('page.aiProbe.lastChecked') }}: {{ result.checked_at }}
        </span>
        <NButton type="primary" size="small" :loading="loading" @click="fetchProbe">
          {{ $t('page.aiProbe.reprobe') }}
        </NButton>
      </div>
    </div>

    <div v-if="result" class="grid gap-4 md:grid-cols-3">
      <NCard v-for="item in result.items" :key="item.key" size="small" :title="itemName(item)" segmented>
        <div class="flex flex-col gap-2">
          <div class="flex items-center gap-2">
            <NTag :type="statusTagType(item.status)" size="small">
              {{ $t(`page.aiProbe.${statusLabel(item.status)}`) }}
            </NTag>
            <span v-if="item.latency_ms > 0" class="text-xs text-[var(--n-text-color-3)]">
              {{ item.latency_ms }} ms
            </span>
          </div>
          <p class="text-sm break-all text-[var(--n-text-color-3)]">{{ item.detail }}</p>
        </div>
      </NCard>
    </div>

    <NEmpty v-else-if="!loading" :description="$t('common.noData')" />
  </div>
</template>
