<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import { resourceApi } from '@/service/api/resources';

interface ResourceItem {
  id: string;
  url: string;
  file_type: string;
  mime: string;
  file_size: number;
  name: string;
  created_at: string;
  object_key: string;
  deleted_at?: string | null;
}

const dialog = useDialog();
const message = useMessage();

const typeTabs = [
  { key: '', label: '全部', icon: 'mdi:view-grid-outline' },
  { key: 'image', label: '图片', icon: 'mdi:image-outline' },
  { key: 'video', label: '视频', icon: 'mdi:video-outline' },
  { key: 'audio', label: '音频', icon: 'mdi:music-note-outline' },
  { key: 'document', label: '文档', icon: 'mdi:file-document-outline' }
];

const activeType = ref('');
const keyword = ref('');
const items = ref<ResourceItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(24);
const loading = ref(false);
const uploading = ref(false);
const selectedIds = ref<Set<string>>(new Set());
const currentDetail = ref<ResourceItem | null>(null);
const currentRefs = ref<Array<{ ref_type: string; ref_id: string; ref_label: string }>>([]);
const renameValue = ref('');
const fileInput = ref<HTMLInputElement | null>(null);
const previewVisible = ref(false);
const previewUrl = ref('');
const previewType = ref<'image' | 'video' | 'audio' | 'other'>('other');

const typeCounts = computed(() => {
  const map: Record<string, number> = {};
  for (const t of typeTabs) {
    if (!t.key) continue;
    map[t.key] = items.value.filter(i => i.file_type === t.key).length;
  }
  return map;
});

const currentDetailRefsLabel = computed(() =>
  currentRefs.value.map(r => r.ref_label).join('、') || '无引用'
);

function formatSize(size: number) {
  if (!size) return '-';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(2)} MB`;
}

function formatTime(t?: string) {
  if (!t) return '-';
  return new Date(t).toLocaleString();
}

function isPreviewableImage(r: ResourceItem) {
  return r.file_type === 'image';
}

function isPreviewableVideo(r: ResourceItem) {
  return r.file_type === 'video';
}

function isPreviewableAudio(r: ResourceItem) {
  return r.file_type === 'audio';
}

function openPreview(r: ResourceItem) {
  previewUrl.value = r.url;
  previewType.value = isPreviewableImage(r)
    ? 'image'
    : isPreviewableVideo(r)
      ? 'video'
      : isPreviewableAudio(r)
        ? 'audio'
        : 'other';
  previewVisible.value = true;
}

async function loadList() {
  loading.value = true;
  try {
    const res = await resourceApi.list({
      type: activeType.value || undefined,
      keyword: keyword.value || undefined,
      page: page.value,
      pageSize: pageSize.value
    });
    const data = (res as any).data ?? res;
    items.value = data.items ?? [];
    total.value = data.total ?? 0;
  } catch (e: any) {
    message.error(`加载资源失败: ${e?.message || e}`);
  } finally {
    loading.value = false;
  }
}

function selectType(key: string) {
  activeType.value = key;
  page.value = 1;
  loadList();
}

function onSearch() {
  page.value = 1;
  loadList();
}

function onPageChange(p: number) {
  page.value = p;
  loadList();
}

function triggerUpload() {
  fileInput.value?.click();
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  try {
    const res = await resourceApi.upload(file);
    message.success('上传成功');
    await loadList();
    const data = (res as any).data;
    if (data?.id) selectDetail(data);
  } catch (err: any) {
    message.error(`上传失败: ${err?.message || err}`);
  } finally {
    uploading.value = false;
    input.value = '';
  }
}

function toggleSelect(id: string) {
  const s = new Set(selectedIds.value);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  selectedIds.value = s;
}

async function selectDetail(r: ResourceItem) {
  currentDetail.value = r;
  renameValue.value = r.name;
  currentRefs.value = [];
  try {
    const res = await resourceApi.detail(r.id);
    const data = (res as any).data?.data ?? (res as any).data ?? res;
    currentDetail.value = data;
    currentRefs.value = data?.refs ?? [];
    renameValue.value = data?.name ?? r.name;
  } catch (e) {
    currentRefs.value = [];
  }
}

async function doRename() {
  if (!currentDetail.value) return;
  const name = renameValue.value.trim();
  if (!name) {
    message.warning('名称不能为空');
    return;
  }
  try {
    await resourceApi.rename(currentDetail.value.id, name);
    message.success('重命名成功');
    currentDetail.value.name = name;
    await loadList();
  } catch (e: any) {
    message.error(`重命名失败: ${e?.message || e}`);
  }
}

async function doDelete(r: ResourceItem) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除资源「${r.name}」吗？（软删，不影响已引用位置）`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { error } = await resourceApi.remove(r.id) as any;
      if (error) {
        message.error(`删除失败: ${error.response?.data?.detail || error.message}`);
        return;
      }
      message.success('已删除');
      selectedIds.value.delete(r.id);
      selectedIds.value = new Set(selectedIds.value);
      if (currentDetail.value?.id === r.id) currentDetail.value = null;
      await loadList();
    }
  });
}

async function doBatchDelete() {
  const ids = Array.from(selectedIds.value);
  if (!ids.length) {
    message.warning('请先选择资源');
    return;
  }
  dialog.warning({
    title: '确认批量删除',
    content: `确定删除选中的 ${ids.length} 个资源吗？（软删）`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { data, error } = await resourceApi.batchRemove(ids) as any;
      if (error) {
        message.error(`批量删除失败: ${error.response?.data?.detail || error.message}`);
        return;
      }
      message.success(`已删除 ${data?.deleted ?? ids.length} 个`);
      selectedIds.value = new Set();
      currentDetail.value = null;
      await loadList();
    }
  });
}

function handleDeleteBySelection() {
  const ids = Array.from(selectedIds.value);
  if (ids.length === 1) {
    const r = items.value.find(it => it.id === ids[0]);
    if (r) doDelete(r);
  } else if (ids.length > 1) {
    doBatchDelete();
  }
}

async function copyUrl(url: string) {
  try {
    await navigator.clipboard.writeText(url);
    message.success('URL 已复制');
  } catch {
    message.error('复制失败');
  }
}

function download(r: ResourceItem) {
  window.open(r.url, '_blank');
}

onMounted(loadList);
</script>

<template>
  <div class="resource-page flex gap-4" style="min-height: calc(100vh - 180px)">
    <!-- 左：资源类型列表 -->
    <div class="flex w-[200px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <div class="flex items-center gap-2 border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700">
        <SvgIcon icon="mdi:folder-multiple-image" class="text-18px text-green-600" />
        <span class="text-sm font-semibold">资源管理</span>
      </div>
      <div class="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
        <div
          v-for="t in typeTabs"
          :key="t.key"
          class="flex cursor-pointer items-center justify-between rounded px-2 py-2 text-sm transition-colors"
          :class="activeType === t.key
            ? 'bg-green-50 text-green-700 font-medium dark:bg-green-900/20 dark:text-green-400'
            : 'hover:bg-gray-50 dark:hover:bg-gray-800'"
          @click="selectType(t.key)"
        >
          <span class="flex items-center gap-2">
            <SvgIcon :icon="t.icon" class="text-16px shrink-0" />
            {{ t.label }}
          </span>
          <span
            v-if="t.key && typeCounts[t.key]"
            class="rounded-full bg-gray-100 px-1.5 text-xs text-gray-500 dark:bg-gray-800"
          >{{ typeCounts[t.key] }}</span>
        </div>
      </div>
    </div>

    <!-- 中：资源列表 -->
    <div class="flex flex-1 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <!-- 工具栏 -->
      <div class="flex items-center justify-between gap-2 border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700">
        <div class="flex items-center gap-2">
          <NButton type="primary" size="small" :loading="uploading" @click="triggerUpload">
            <template #icon><SvgIcon icon="mdi:upload" class="text-16px" /></template>
            上传资源
          </NButton>
          <NButton size="small" type="error" secondary :disabled="!selectedIds.size" @click="handleDeleteBySelection">
            <template #icon><SvgIcon :icon="selectedIds.size > 1 ? 'mdi:delete-sweep-outline' : 'mdi:delete-outline'" class="text-16px" /></template>
            {{ selectedIds.size > 1 ? '批量删除' : '删除' }}
          </NButton>
          <input ref="fileInput" type="file" class="hidden" @change="onFileChange" />
        </div>
        <div class="flex items-center gap-2">
          <NButton size="small" @click="loadList">
            <template #icon><SvgIcon icon="mdi:refresh" class="text-16px" /></template>
            刷新
          </NButton>
          <NInput
            v-model:value="keyword"
            placeholder="搜索名称 / URL"
            size="small"
            clearable
            style="width: 220px"
            @keyup.enter="onSearch"
          >
            <template #prefix><SvgIcon icon="mdi:magnify" class="text-14px" /></template>
          </NInput>
          <NButton size="small" @click="onSearch">搜索</NButton>
        </div>
      </div>

      <!-- 缩略图网格 -->
      <div class="flex-1 overflow-y-auto p-3">
        <NSpin :show="loading">
          <div v-if="!items.length && !loading" class="flex flex-col items-center justify-center py-20 text-gray-400">
            <SvgIcon icon="mdi:image-off-outline" class="text-40px mb-2" />
            <span>暂无资源，点击右上角上传</span>
          </div>
          <div v-else class="grid grid-cols-4 gap-3 xl:grid-cols-5">
            <div
              v-for="r in items"
              :key="r.id"
              class="group relative cursor-pointer overflow-hidden rounded-lg border border-gray-100 border-solid dark:border-gray-700"
              :class="currentDetail?.id === r.id ? 'ring-2 ring-green-500' : ''"
              @click="selectDetail(r)"
            >
              <div class="flex h-[110px] items-center justify-center bg-gray-50 dark:bg-gray-800">
                <img v-if="isPreviewableImage(r)" :src="r.url" class="h-full w-full object-cover" loading="lazy" />
                <div v-else-if="isPreviewableVideo(r)" class="flex flex-col items-center text-gray-400">
                  <SvgIcon icon="mdi:play-circle-outline" class="text-30px" />
                  <span class="mt-1 text-xs">视频</span>
                </div>
                <div v-else-if="isPreviewableAudio(r)" class="flex flex-col items-center text-gray-400">
                  <SvgIcon icon="mdi:music-note" class="text-30px" />
                  <span class="mt-1 text-xs">音频</span>
                </div>
                <div v-else class="flex flex-col items-center text-gray-400">
                  <SvgIcon icon="mdi:file-document-outline" class="text-30px" />
                  <span class="mt-1 text-xs">文档</span>
                </div>
              </div>
              <div
                v-if="isPreviewableImage(r) || isPreviewableVideo(r) || isPreviewableAudio(r)"
                class="absolute inset-0 z-10 hidden cursor-zoom-in items-center justify-center bg-black/30 group-hover:flex"
                @click.stop="openPreview(r)"
              >
                <SvgIcon icon="mdi:magnify-plus-outline" class="text-32px text-white" />
              </div>
              <div class="truncate px-2 py-1.5 text-xs" :title="r.name">{{ r.name }}</div>
              <div
                class="absolute top-1.5 right-1.5 z-20 flex h-5 w-5 cursor-pointer items-center justify-center rounded border border-solid text-xs transition-colors"
                :class="selectedIds.has(r.id)
                  ? 'border-green-500 bg-green-500 text-white'
                  : 'border-gray-300 bg-white text-gray-400 dark:border-gray-500 dark:bg-gray-700'"
                @click.stop="toggleSelect(r.id)"
              >
                <SvgIcon v-if="selectedIds.has(r.id)" icon="mdi:check" class="text-12px" />
              </div>
            </div>
          </div>
        </NSpin>
      </div>

      <!-- 分页 -->
      <div class="flex items-center justify-between border-t border-gray-100 border-solid px-4 py-2 dark:border-gray-700">
        <span class="text-xs text-gray-500">共 {{ total }} 个资源</span>
        <NPagination
          :page="page"
          :page-size="pageSize"
          :item-count="total"
          size="small"
          @update:page="onPageChange"
        />
      </div>
    </div>

    <!-- 右：详情 -->
    <div class="flex w-[300px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <div class="border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700">
        <span class="text-sm font-semibold">资源详情</span>
      </div>
      <div v-if="currentDetail" class="flex-1 overflow-y-auto p-4">
        <!-- 预览 -->
        <div
          class="mb-3 flex h-[160px] cursor-zoom-in items-center justify-center overflow-hidden rounded bg-gray-50 dark:bg-gray-800"
          @click="openPreview(currentDetail)"
        >
          <img v-if="isPreviewableImage(currentDetail)" :src="currentDetail.url" class="h-full w-full object-contain" />
          <video v-else-if="isPreviewableVideo(currentDetail)" :src="currentDetail.url" controls class="h-full w-full" />
          <audio v-else-if="isPreviewableAudio(currentDetail)" :src="currentDetail.url" controls class="w-full px-3" />
          <SvgIcon v-else icon="mdi:file-document-outline" class="text-40px text-gray-400" />
        </div>

        <!-- 名称重命名 -->
        <div class="mb-3">
          <div class="mb-1 text-xs text-gray-500">名称</div>
          <div class="flex items-center gap-1">
            <NInput v-model:value="renameValue" size="small" />
            <NButton size="small" @click="doRename">保存</NButton>
          </div>
        </div>

        <!-- 元信息 -->
        <div class="mb-3 space-y-2 text-xs">
          <div class="flex justify-between"><span class="text-gray-500">类型</span><span>{{ currentDetail.file_type }} / {{ currentDetail.mime }}</span></div>
          <div class="flex justify-between"><span class="text-gray-500">大小</span><span>{{ formatSize(currentDetail.file_size) }}</span></div>
          <div class="flex justify-between"><span class="text-gray-500">上传时间</span><span>{{ formatTime(currentDetail.created_at) }}</span></div>
          <div class="flex justify-between gap-2">
            <span class="text-gray-500 shrink-0">MinIO 路径</span>
            <span class="truncate" :title="currentDetail.object_key || currentDetail.url">{{ currentDetail.object_key || '-' }}</span>
          </div>
          <div class="flex justify-between gap-2">
            <span class="text-gray-500 shrink-0">引用位置</span>
            <span class="truncate text-right" :title="currentDetailRefsLabel">{{ currentDetailRefsLabel }}</span>
          </div>
        </div>

        <!-- 操作 -->
        <div class="flex flex-col gap-2">
          <div class="flex items-center gap-2">
            <NButton size="small" type="primary" block @click="copyUrl(currentDetail.url)">
              <template #icon><SvgIcon icon="mdi:content-copy" class="text-14px" /></template>
              复制 URL
            </NButton>
          </div>
          <div class="flex items-center gap-2">
            <NButton size="small" block @click="download(currentDetail)">
              <template #icon><SvgIcon icon="mdi:download" class="text-14px" /></template>
              下载
            </NButton>
            <NButton size="small" type="error" secondary block @click="doDelete(currentDetail)">
              <template #icon><SvgIcon icon="mdi:delete-outline" class="text-14px" /></template>
              删除
            </NButton>
          </div>
        </div>
      </div>
      <div v-else class="flex flex-1 flex-col items-center justify-center text-gray-400">
        <SvgIcon icon="mdi:image-search-outline" class="text-40px mb-2" />
        <span class="text-sm">选择左侧资源查看详情</span>
      </div>
    </div>

    <NModal
      v-model:show="previewVisible"
      preset="card"
      :title="previewType === 'image' ? '图片预览' : previewType === 'video' ? '视频预览' : previewType === 'audio' ? '音频预览' : '资源预览'"
      style="width: 80%; max-width: 960px"
    >
      <div class="flex items-center justify-center">
        <img v-if="previewType === 'image'" :src="previewUrl" class="max-h-[70vh] max-w-full object-contain" alt="预览" />
        <video v-else-if="previewType === 'video'" :src="previewUrl" controls autoplay class="max-h-[70vh] max-w-full" />
        <audio v-else-if="previewType === 'audio'" :src="previewUrl" controls autoplay class="w-full" />
        <div v-else class="flex flex-col items-center gap-2 py-10 text-gray-400">
          <SvgIcon icon="mdi:file-document-outline" class="text-60px" />
          <span class="text-sm">该类型暂不支持预览，可通过下载查看</span>
        </div>
      </div>
    </NModal>
  </div>
</template>

<style scoped>
.hidden {
  display: none;
}
</style>
