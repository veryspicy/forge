<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  NButton,
  NEmpty,
  NImage,
  NInput,
  NModal,
  NScrollbar,
  NPagination,
  NSpin,
  NTabPane,
  NTabs,
  NUpload,
  NUploadDragger,
  useMessage
} from 'naive-ui';
import { resourceApi } from '@/service/api/resources';

export interface ResourceItem {
  id: string;
  url: string;
  thumb_url?: string;
  name?: string;
  file_type?: string;
  [key: string]: any;
}

const props = withDefaults(
  defineProps<{
    show: boolean;
    multiple?: boolean;
    type?: 'image' | 'video' | 'audio' | 'document' | '';
    title?: string;
    uploadDirectory?: string;
  }>(),
  {
    multiple: false,
    type: 'image',
    title: '选择资源',
    uploadDirectory: ''
  }
);

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void;
  (e: 'confirm', items: ResourceItem[]): void;
}>();

const message = useMessage();

const keyword = ref('');
const page = ref(1);
const pageSize = 24;
const total = ref(0);
const loading = ref(false);
const list = ref<ResourceItem[]>([]);
const selected = ref<ResourceItem[]>([]);
const activeTab = ref<'library' | 'upload'>('library');

// 上传态
const uploading = ref(false);

const previewUrl = (item: ResourceItem) => item.thumb_url || item.url;

const isImage = (item: ResourceItem) => item.file_type === 'image';

async function fetchList() {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: page.value,
      pageSize,
      keyword: keyword.value || undefined
    };
    if (props.type) params.type = props.type;
    const res = await resourceApi.list(params);
    const data = res?.data?.data || res?.data || { items: [], total: 0 };
    list.value = data.items || [];
    total.value = data.total || 0;
  } catch {
    message.error('资源列表加载失败');
  } finally {
    loading.value = false;
  }
}

function isSelected(item: ResourceItem) {
  return selected.value.some(s => s.id === item.id);
}

function toggleSelect(item: ResourceItem) {
  if (props.multiple) {
    if (isSelected(item)) {
      selected.value = selected.value.filter(s => s.id !== item.id);
    } else {
      selected.value = [...selected.value, item];
    }
  } else {
    selected.value = [item];
  }
}

async function handleUpload({ file, onFinish, onError }: any) {
  uploading.value = true;
  try {
    const res = await resourceApi.upload(file.file as File, {
      directory: props.uploadDirectory || undefined
    });
    const data = res?.data?.data || res?.data;
    if (!data?.id) throw new Error('no id');
    const item: ResourceItem = {
      id: data.id,
      url: data.url,
      thumb_url: data.thumb_url,
      name: data.name,
      file_type: data.file_type
    };
    if (props.multiple) {
      if (!isSelected(item)) selected.value = [...selected.value, item];
    } else {
      selected.value = [item];
    }
    message.success('上传成功');
    onFinish?.();
    await fetchList();
  } catch {
    message.error('上传失败');
    onError?.();
  } finally {
    uploading.value = false;
  }
}

function handleConfirm() {
  emit('confirm', [...selected.value]);
  close();
}

function close() {
  emit('update:show', false);
}

watch(
  () => props.show,
  v => {
    if (v) {
      selected.value = [];
      page.value = 1;
      keyword.value = '';
      activeTab.value = 'library';
      fetchList();
    }
  }
);

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    style="width: 760px; max-width: 92vw"
    @update:show="v => emit('update:show', v)"
  >
    <NTabs v-model:value="activeTab" type="line">
      <NTabPane name="library" tab="从资源库选择">
        <div class="flex items-center gap-2 pb-2">
          <NInput
            v-model:value="keyword"
            placeholder="搜索资源名称"
            clearable
            class="flex-1"
            @keyup.enter="fetchList"
            @clear="fetchList"
          />
          <NButton size="small" @click="fetchList">搜索</NButton>
        </div>
        <NScrollbar style="max-height: 420px">
          <NSpin :show="loading">
            <div v-if="!list.length && !loading" class="py-10">
              <NEmpty description="暂无资源" />
            </div>
            <div v-else class="grid grid-cols-4 gap-3">
              <div
                v-for="item in list"
                :key="item.id"
                class="group relative cursor-pointer rounded border p-2 transition"
                :class="isSelected(item) ? 'border-primary bg-primary/5' : 'border-gray-200 hover:border-primary'"
                @click="toggleSelect(item)"
              >
                <div class="flex h-24 items-center justify-center overflow-hidden rounded bg-gray-50">
                  <NImage v-if="isImage(item)" :src="previewUrl(item)" object-fit="contain" class="h-full w-full" />
                  <div v-else class="text-xs text-gray-400">
                    {{ item.file_type || '文件' }}
                  </div>
                </div>
                <div class="mt-1 truncate text-xs text-gray-500" :title="item.name">
                  {{ item.name }}
                </div>
                <div
                  v-if="isSelected(item)"
                  class="absolute right-1 top-1 rounded bg-primary px-1 text-[10px] text-white"
                >
                  {{ multiple ? '已选' : '选中' }}
                </div>
              </div>
            </div>
          </NSpin>
        </NScrollbar>
        <div v-if="total > pageSize" class="mt-2 flex justify-end">
          <NPagination
            v-model:page="page"
            :page-count="totalPages"
            :page-size="pageSize"
            size="small"
            @update:page="fetchList"
          />
        </div>
      </NTabPane>

      <NTabPane name="upload" tab="上传新资源">
        <NUpload :show-file-list="false" accept="image/*" :custom-request="handleUpload" class="py-6">
          <NUploadDragger class="flex flex-col items-center justify-center gap-2 py-10">
            <div class="text-sm text-gray-500">
              {{ uploading ? '上传中…' : '点击或拖拽图片到此处上传' }}
            </div>
            <div class="text-xs text-gray-400">上传后自动加入已选列表</div>
          </NUploadDragger>
        </NUpload>
      </NTabPane>
    </NTabs>

    <template #footer>
      <div class="flex items-center justify-between">
        <span class="text-xs text-gray-400">已选 {{ selected.length }} 项</span>
        <div class="flex gap-2">
          <NButton size="small" @click="close">取消</NButton>
          <NButton size="small" type="primary" :disabled="!selected.length" @click="handleConfirm">确定</NButton>
        </div>
      </div>
    </template>
  </NModal>
</template>
