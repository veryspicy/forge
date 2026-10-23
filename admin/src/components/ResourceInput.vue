<script setup lang="ts">
import { computed, ref } from 'vue';
import { NButton, NInput, NUpload, useMessage } from 'naive-ui';
import { resourceApi } from '@/service/api/resources';
import ResourcePickerModal, { type ResourceItem } from './ResourcePickerModal.vue';

/**
 * 媒体资源三入口统一组件（RESOURCE-INPUT）。
 *
 * 对图片 / 视频 / 音频 / 文档统一提供三种取值方式：
 * 1. 上传：直传资源库（resourceApi.upload），返回 URL 写入当前值
 * 2. 粘贴 URL：站内相对路径直接使用；http(s) 外链调用 registerExternal 幂等登记为资源
 * 3. 资源库：打开 ResourcePickerModal 按类型选择，选中项的 url 写入当前值
 *
 * modelValue 约定：
 * - multiple=false：string，空串表示无值
 * - multiple=true：string[]（图片块的 images 数组即复用该模式）
 */
const props = withDefaults(
  defineProps<{
    modelValue?: string | string[] | null | undefined;
    type?: 'image' | 'video' | 'audio' | 'document';
    multiple?: boolean;
    placeholder?: string;
    uploadDirectory?: string;
  }>(),
  {
    modelValue: '',
    type: 'image',
    multiple: false,
    placeholder: '粘贴资源 URL，如 https://...',
    uploadDirectory: ''
  }
);

const emit = defineEmits<{
  (e: 'update:modelValue', v: string | string[]): void;
  (e: 'register', item: ResourceItem): void;
}>();

const message = useMessage();

const urlInput = ref('');
const pickerShow = ref(false);
const uploading = ref(false);

const items = computed<string[]>({
  get: () => {
    const v = props.modelValue;
    if (props.multiple) return Array.isArray(v) ? v.map(toUrlStr).filter(Boolean) : [];
    const s = toUrlStr(v);
    return s ? [s] : [];
  },
  set: (arr: string[]) => {
    emit('update:modelValue', props.multiple ? arr : (arr[0] ?? ''));
  }
});

/** 资源值归一化：字符串直返；历史对象 { url, resource_id } 取 url，保证编辑态回显旧数据 */
function toUrlStr(v: unknown): string {
  if (typeof v === 'string') return v;
  if (v && typeof v === 'object') {
    const obj = v as Record<string, unknown>;
    const u = obj.url ?? obj.src;
    return typeof u === 'string' ? u : '';
  }
  return '';
}

const acceptStr = computed(() => {
  const map: Record<string, string> = {
    image: 'image/*',
    video: 'video/*',
    audio: 'audio/*',
    document: '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt,.zip'
  };
  return map[props.type] || 'image/*';
});

const typeLabel = computed(() => {
  const map: Record<string, string> = { image: '图片', video: '视频', audio: '音频', document: '文件' };
  return map[props.type] || '资源';
});

function addUrl(url: string): void {
  const u = url.trim();
  if (!u) return;
  if (items.value.includes(u)) return;
  items.value = [...items.value, u];
}

function removeAt(idx: number): void {
  items.value = items.value.filter((_, j) => j !== idx);
}

async function handleUpload({ file, onFinish, onError }: any) {
  uploading.value = true;
  try {
    const res = await resourceApi.upload(file.file as File, { directory: props.uploadDirectory || undefined });
    const data = res?.data?.data || res?.data;
    if (!data?.url) throw new Error('no url');
    addUrl(data.url);
    emit('register', data);
    message.success('上传成功');
    onFinish?.();
  } catch {
    message.error('上传失败');
    onError?.();
  } finally {
    uploading.value = false;
  }
}

/** 粘贴 URL：站内路径直接使用；外链登记为资源后写入（登记失败按原链接降级使用） */
async function confirmUrl() {
  const url = urlInput.value.trim();
  if (!url) return;
  if (url.startsWith('/uploads/') || url.startsWith('/minio/')) {
    addUrl(url);
    urlInput.value = '';
    return;
  }
  if (!/^https?:\/\//i.test(url)) {
    message.warning('请输入 http(s) 链接或站内资源路径');
    return;
  }
  try {
    const res = await resourceApi.registerExternal({ url, fileType: props.type });
    const data = res?.data?.data || res?.data;
    addUrl(data?.url || url);
    if (data) emit('register', data);
    message.success('已登记为资源');
  } catch {
    message.error('URL 登记失败，已按原链接使用');
    addUrl(url);
  }
  urlInput.value = '';
}

function onPickerConfirm(list: ResourceItem[]) {
  list.forEach(item => addUrl(item.url || ''));
}

function itemName(url: string): string {
  try {
    return decodeURIComponent(url.split('/').pop() || url);
  } catch {
    return url;
  }
}
</script>

<template>
  <div class="resource-input">
    <!-- 当前值预览列表 -->
    <div v-if="items.length" class="mb-2 flex flex-wrap gap-2">
      <div
        v-for="(url, idx) in items"
        :key="`${url}-${idx}`"
        class="group relative overflow-hidden rounded-md border border-[var(--n-border-color)]"
      >
        <img v-if="type === 'image'" :src="url" alt="" class="h-16 w-16 object-cover" />
        <div v-else class="flex h-16 w-24 items-center justify-center bg-gray-50 text-xs text-gray-500">
          {{ typeLabel }}
        </div>
        <NButton
          size="tiny"
          circle
          type="error"
          class="absolute right-0.5 top-0.5 opacity-0 transition group-hover:opacity-100"
          @click="removeAt(idx)"
        >
          ×
        </NButton>
        <div class="max-w-24 truncate px-1 py-0.5 text-[10px] text-gray-400" :title="itemName(url)">
          {{ itemName(url) }}
        </div>
      </div>
    </div>

    <!-- 三入口：上传 / 粘贴 URL / 资源库 -->
    <div class="flex flex-wrap items-center gap-2">
      <NUpload :accept="acceptStr" :show-file-list="false" :custom-request="handleUpload" :disabled="uploading">
        <NButton size="small" :loading="uploading">上传</NButton>
      </NUpload>
      <NInput
        v-model:value="urlInput"
        size="small"
        :placeholder="placeholder"
        clearable
        class="!w-64"
        @keyup.enter="confirmUrl"
      />
      <NButton size="small" @click="confirmUrl">登记 URL</NButton>
      <NButton size="small" @click="pickerShow = true">从资源库选择</NButton>
    </div>
    <div class="mt-1 text-xs opacity-50">{{ typeLabel }}支持上传 / 粘贴 URL / 资源库选择三种方式</div>

    <ResourcePickerModal
      v-model:show="pickerShow"
      :type="type"
      :multiple="multiple"
      :upload-directory="uploadDirectory"
      @confirm="onPickerConfirm"
    />
  </div>
</template>
