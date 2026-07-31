<template>
  <div class="diy-editor h-full flex flex-col gap-3">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between rounded bg-white p-3 shadow-sm dark:bg-dark">
      <div class="flex items-center gap-3">
        <NButton quaternary @click="goBack">
          <template #icon><SvgIcon icon="mdi:arrow-left" /></template>
          Back
        </NButton>
        <span class="text-base font-semibold">{{ store.currentPage?.name || '...' }}</span>
        <NTag v-if="store.currentPage" size="small" :type="store.currentPage.status === 'published' ? 'success' : 'default'">
          {{ store.currentPage.status }}
        </NTag>
        <NTag v-if="store.currentPage?.is_default" size="small" type="info">HOME</NTag>
      </div>
      <NSpace>
        <NButton :loading="saving" @click="save">Save Draft</NButton>
        <NButton @click="preview">Preview</NButton>
        <NButton type="primary" :loading="publishing" @click="publish">Publish</NButton>
      </NSpace>
    </div>

    <!-- 三栏布局 -->
    <div class="flex flex-1 gap-4 overflow-hidden" style="min-height: calc(100vh - 220px)">
      <ComponentPanel class="w-[280px] shrink-0" />
      <PreviewCanvas class="flex-1" />
      <PropertyPanel class="w-[360px] shrink-0" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NButton, NSpace, NTag } from 'naive-ui';
import { useDiyStore } from '@/store/modules/diy';
import { diyApi } from '@/service/api/diy';
import ComponentPanel from './modules/ComponentPanel.vue';
import PreviewCanvas from './modules/PreviewCanvas.vue';
import PropertyPanel from './modules/PropertyPanel.vue';

const route = useRoute();
const router = useRouter();
const store = useDiyStore();

const saving = ref(false);
const publishing = ref(false);

const pageId = route.params.id as string;

async function save() {
  saving.value = true;
  try {
    await store.saveComponents(pageId);
    window.$message?.success('Saved');
  } finally {
    saving.value = false;
  }
}

async function publish() {
  publishing.value = true;
  try {
    await store.saveComponents(pageId);
    const res = await diyApi.publishPage(pageId);
    if (store.currentPage) {
      store.currentPage.status = res.data?.status || 'published';
    }
    window.$message?.success('Published');
  } finally {
    publishing.value = false;
  }
}

function preview() {
  const slug = store.currentPage?.slug;
  if (slug) {
    window.open(`/api/v1/diy/pages/${slug}?preview=true`, '_blank');
  }
}

function goBack() {
  router.push('/diy/pages');
}

onMounted(async () => {
  store.reset();
  await Promise.all([store.fetchComponentsLibrary(), store.fetchPage(pageId)]);
});

onUnmounted(() => {
  store.reset();
});
</script>

<style scoped>
.diy-editor {
  min-height: 100%;
}
</style>
