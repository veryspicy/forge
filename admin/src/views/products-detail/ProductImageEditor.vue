<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import Cropper from 'cropperjs';
import { NButton, NModal, NSpace, NRadioGroup, NRadioButton } from 'naive-ui';

/**
 * 图片裁剪组件（CROPPER.JS v2）。
 * 自由 / 1:1 / 4:3 / 3:4 / 16:9 比例，确认后导出 PNG File 与预览 dataURL，emit save。
 */
const props = defineProps<{ show: boolean; imageUrl: string }>();
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void;
  (e: 'save', payload: { file: File; dataUrl: string }): void;
}>();

const containerRef = ref<HTMLDivElement | null>(null);
const cropper = ref<Cropper | null>(null);
const ratio = ref<number>(NaN); // NaN = 自由
const saving = ref(false);

const ratioOptions = [
  { label: '自由', value: NaN },
  { label: '1:1', value: 1 },
  { label: '4:3', value: 4 / 3 },
  { label: '3:4', value: 3 / 4 },
  { label: '16:9', value: 16 / 9 }
];

function setRatio(v: number) {
  ratio.value = v;
  const sel = cropper.value?.getCropperSelection();
  if (sel) sel.aspectRatio = v;
}

function applyRatioToSelection() {
  const sel = cropper.value?.getCropperSelection();
  if (sel) sel.aspectRatio = ratio.value;
}

watch(
  () => props.show,
  v => {
    if (v) {
      ratio.value = NaN;
      // 等 DOM 渲染后再初始化
      requestAnimationFrame(initCropper);
    } else {
      destroyCropper();
    }
  }
);

function initCropper() {
  destroyCropper();
  const wrap = containerRef.value;
  if (!wrap) return;
  const canvasEl = wrap.querySelector('cropper-canvas');
  if (!canvasEl) return;
  cropper.value = new Cropper(canvasEl as unknown as HTMLCanvasElement, { container: wrap });
  applyRatioToSelection();
}

function destroyCropper() {
  cropper.value?.destroy();
  cropper.value = null;
}

onMounted(() => {
  if (props.show) requestAnimationFrame(initCropper);
});
onBeforeUnmount(destroyCropper);

async function confirm() {
  const c = cropper.value;
  if (!c) return;
  const canvas = c.getCropperCanvas();
  if (!canvas) return;
  saving.value = true;
  try {
    const real = await canvas.$toCanvas({ width: 1600 });
    const blob: Blob | null = await new Promise(resolve => real.toBlob(resolve, 'image/png'));
    if (!blob) throw new Error('导出失败');
    const file = new File([blob], 'cropped.png', { type: 'image/png' });
    const dataUrl = real.toDataURL('image/png');
    emit('save', { file, dataUrl });
    emit('update:show', false);
  } finally {
    saving.value = false;
  }
}

function close() {
  emit('update:show', false);
}
</script>

<template>
  <NModal
    :show="props.show"
    preset="card"
    title="裁剪图片"
    style="width: 760px"
    @update:show="(v: boolean) => (v ? undefined : close())"
  >
    <div ref="containerRef" class="w-full overflow-hidden rounded-lg bg-black">
      <CropperCanvas background class="cropper-canvas-host">
        <CropperImage :src="props.imageUrl" alt="待裁剪图片" />
        <CropperSelection initial-coverage="0.8" outlined movable resizable />
      </CropperCanvas>
    </div>

    <div class="flex items-center justify-between mt-3">
      <NRadioGroup :value="ratio" @update:value="setRatio">
        <NRadioButton v-for="opt in ratioOptions" :key="String(opt.value)" :value="opt.value">
          {{ opt.label }}
        </NRadioButton>
      </NRadioGroup>
      <span class="text-xs opacity-60">拖拽选区、滚轮缩放</span>
    </div>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="close">取消</NButton>
        <NButton type="primary" :loading="saving" @click="confirm">确认裁剪</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
.cropper-canvas-host {
  display: block;
  width: 100%;
  height: 420px;
}
</style>
