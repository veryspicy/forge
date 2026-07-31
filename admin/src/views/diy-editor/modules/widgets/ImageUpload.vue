<template>
  <div class="w-full">
    <div v-if="modelValue" class="relative inline-block">
      <NImage :src="modelValue" width="120" height="80" object-fit="cover" class="rounded" />
      <NButton
        size="tiny"
        circle
        type="error"
        class="absolute -right-2 -top-2 z-10"
        @click="$emit('update:modelValue', '')"
      >
        <template #icon><SvgIcon icon="mdi:close" /></template>
      </NButton>
    </div>
    <NUpload
      v-else
      :custom-request="handleUpload"
      :show-file-list="false"
      accept="image/*"
    >
      <NButton size="small" dashed block :loading="uploading">
        <template #icon><SvgIcon icon="mdi:upload" /></template>
        上传图片
      </NButton>
    </NUpload>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { NButton, NImage, NUpload } from 'naive-ui';
import type { UploadCustomRequestOptions } from 'naive-ui';
import { diyApi } from '@/service/api/diy';

defineProps<{
  modelValue?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const uploading = ref(false);

async function handleUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  uploading.value = true;
  try {
    const res = await diyApi.uploadImage(file.file as File);
    emit('update:modelValue', res.data?.url || '');
    window.$message?.success('上传成功');
    onFinish();
  } catch (e) {
    onError();
  } finally {
    uploading.value = false;
  }
}
</script>
