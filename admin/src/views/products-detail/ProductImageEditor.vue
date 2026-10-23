<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import Cropper, { CropperCanvas, CropperImage, CropperSelection } from 'cropperjs';
import { NButton, NModal, NSpace, NRadioGroup, NRadioButton, NColorPicker, NSelect, NInput } from 'naive-ui';

// cropperjs v2 为 Web Component 架构，需手动注册自定义元素后模板标签才生效
if (typeof customElements !== 'undefined') {
  customElements.define('cropper-canvas', CropperCanvas);
  customElements.define('cropper-image', CropperImage);
  customElements.define('cropper-selection', CropperSelection);
}

/**
 * 商品图片编辑器（CROPPER.JS v2）。
 * 裁剪（自由 / 1:1 / 4:3 / 3:4 / 16:9）、旋转（左/右 90°）、标注（文字 / 矩形 / 圆形 / 箭头）。
 * 确认后导出 PNG File 与预览 dataURL，emit save。
 */

export interface Annotation {
  id: string;
  type: 'text' | 'rect' | 'circle' | 'arrow';
  /** 百分比坐标（相对显示区域） */
  x: number;
  y: number;
  w: number;
  h: number;
  text: string;
  color: string;
  /** 显示字号 px（导出时按比例放大） */
  fontSize: number;
  /** 是否填充（图形标注） */
  fill: boolean;
}

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

/* ---------------- 标注状态 ---------------- */
const annotations = ref<Annotation[]>([]);
const selectedId = ref<string | null>(null);
const editingId = ref<string | null>(null);
const annoColor = ref('#ff4d4f');
const annoFontSize = ref(20);
const annoFill = ref(false);
const fontSizeOptions = [
  { label: '小 14', value: 14 },
  { label: '中 20', value: 20 },
  { label: '大 28', value: 28 },
  { label: '特大 40', value: 40 }
];
const colorPresets = ['#ffffff', '#111111', '#ff4d4f', '#fa8c16', '#faad14', '#52c41a', '#1677ff', '#722ed1'];

function uid() {
  return `a_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function addAnnotation(type: Annotation['type']) {
  const w = type === 'arrow' ? 20 : type === 'text' ? 12 : 24;
  const h = type === 'text' ? 8 : type === 'arrow' ? 20 : type === 'circle' ? 24 : 18;
  const a: Annotation = {
    id: uid(),
    type,
    x: 38,
    y: 30,
    w,
    h,
    text: type === 'text' ? '双击输入文字' : '',
    color: annoColor.value,
    fontSize: annoFontSize.value,
    fill: annoFill.value
  };
  annotations.value.push(a);
  selectedId.value = a.id;
}

function deleteSelected() {
  if (!selectedId.value) return;
  annotations.value = annotations.value.filter(a => a.id !== selectedId.value);
  selectedId.value = null;
  editingId.value = null;
}

function clearAnnotations() {
  annotations.value = [];
  selectedId.value = null;
  editingId.value = null;
}

/* ---------------- 标注渲染样式 ---------------- */
const overlaySize = ref({ w: 0, h: 0 });

function annoTextStyle(a: Annotation) {
  return {
    left: `${a.x}%`,
    top: `${a.y}%`,
    fontSize: `${a.fontSize}px`,
    color: a.color
  };
}

function annoShapeAttrs(a: Annotation) {
  const stroke = a.color;
  const fill = a.fill ? a.color : 'none';
  if (a.type === 'rect') {
    return { x: `${a.x}%`, y: `${a.y}%`, width: `${a.w}%`, height: `${a.h}%`, stroke, fill, 'stroke-width': 2 };
  }
  if (a.type === 'circle') {
    // cx/cy 为圆心，用 x/y 表示圆心坐标
    return { cx: `${a.x}%`, cy: `${a.y}%`, r: `${Math.max(a.w, a.h) / 2}%`, stroke, fill, 'stroke-width': 2 };
  }
  if (a.type === 'arrow') {
    return {
      x1: `${a.x}%`,
      y1: `${a.y}%`,
      x2: `${a.x + a.w}%`,
      y2: `${a.y + a.h}%`,
      stroke,
      'stroke-width': 2
    };
  }
  return {};
}

/* ---------------- 标注拖拽 ---------------- */
const dragState = ref<{ id: string; startClientX: number; startClientY: number; origX: number; origY: number } | null>(null);

function onDragStart(a: Annotation, e: MouseEvent) {
  if (editingId.value === a.id) return;
  selectedId.value = a.id;
  dragState.value = {
    id: a.id,
    startClientX: e.clientX,
    startClientY: e.clientY,
    origX: a.x,
    origY: a.y
  };
}

function onDragMove(e: MouseEvent) {
  const ds = dragState.value;
  const wrap = containerRef.value;
  if (!ds || !wrap) return;
  const rect = wrap.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const target = annotations.value.find(a => a.id === ds.id);
  if (!target) return;
  target.x = Math.min(100, Math.max(0, ds.origX + ((e.clientX - ds.startClientX) / rect.width) * 100));
  target.y = Math.min(100, Math.max(0, ds.origY + ((e.clientY - ds.startClientY) / rect.height) * 100));
}

function onDragEnd() {
  dragState.value = null;
}

function startEditText(a: Annotation) {
  editingId.value = a.id;
  selectedId.value = a.id;
}

function commitEditText(a: Annotation) {
  if (editingId.value === a.id) {
    editingId.value = null;
    a.text = a.text.trim() || '文字';
  }
}

/* ---------------- 旋转 ---------------- */
function rotate(deg: number) {
  const img = cropper.value?.getCropperImage();
  img?.$rotate((deg * Math.PI) / 180);
}

/* ---------------- 裁剪比例 ---------------- */
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
      annotations.value = [];
      selectedId.value = null;
      editingId.value = null;
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
  const rect = wrap.getBoundingClientRect();
  overlaySize.value = { w: rect.width, h: rect.height };
}

function destroyCropper() {
  cropper.value?.destroy();
  cropper.value = null;
}

onMounted(() => {
  if (props.show) requestAnimationFrame(initCropper);
});
onBeforeUnmount(destroyCropper);

/* ---------------- 导出（合成标注） ---------------- */
function drawAnnotations(ctx: CanvasRenderingContext2D, cw: number, ch: number) {
  const scaleW = cw / (overlaySize.value.w || cw);
  const scaleH = ch / (overlaySize.value.h || ch);
  const px = (v: number) => (v / 100) * cw;
  const py = (v: number) => (v / 100) * ch;
  const pw = (v: number) => (v / 100) * cw;
  const ph = (v: number) => (v / 100) * ch;

  for (const a of annotations.value) {
    ctx.save();
    ctx.strokeStyle = a.color;
    ctx.fillStyle = a.color;
    if (a.type === 'text') {
      const fs = Math.max(8, Math.round(a.fontSize * scaleH));
      ctx.font = `${fs}px sans-serif`;
      ctx.textBaseline = 'top';
      const lines = a.text.split('\n');
      lines.forEach((line, i) => {
        ctx.fillText(line, px(a.x), py(a.y) + i * fs * 1.25);
      });
    } else if (a.type === 'rect') {
      ctx.lineWidth = Math.max(1.5, 2 * scaleW);
      if (a.fill) ctx.fillRect(px(a.x), py(a.y), pw(a.w), ph(a.h));
      ctx.strokeRect(px(a.x), py(a.y), pw(a.w), ph(a.h));
    } else if (a.type === 'circle') {
      ctx.lineWidth = Math.max(1.5, 2 * scaleW);
      const r = pw(Math.max(a.w, a.h)) / 2;
      ctx.beginPath();
      ctx.arc(px(a.x), py(a.y), r, 0, Math.PI * 2);
      if (a.fill) ctx.fill();
      ctx.stroke();
    } else if (a.type === 'arrow') {
      ctx.lineWidth = Math.max(2, 3 * scaleW);
      const x1 = px(a.x);
      const y1 = py(a.y);
      const x2 = px(a.x + a.w);
      const y2 = py(a.y + a.h);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      // 箭头三角
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const head = Math.max(8, 12 * scaleW);
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - head * Math.cos(angle - Math.PI / 6), y2 - head * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(x2 - head * Math.cos(angle + Math.PI / 6), y2 - head * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }
}

async function confirm() {
  const c = cropper.value;
  if (!c) return;
  const canvas = c.getCropperCanvas();
  if (!canvas) return;
  saving.value = true;
  try {
    const real = await canvas.$toCanvas({ width: 1600 });
    let out = real;
    if (annotations.value.length) {
      const merged = document.createElement('canvas');
      merged.width = real.width;
      merged.height = real.height;
      const ctx = merged.getContext('2d');
      if (ctx) {
        ctx.drawImage(real, 0, 0);
        drawAnnotations(ctx, merged.width, merged.height);
        out = merged;
      }
    }
    const blob: Blob | null = await new Promise(resolve => out.toBlob(resolve, 'image/png'));
    if (!blob) throw new Error('导出失败');
    const file = new File([blob], 'edited.png', { type: 'image/png' });
    const dataUrl = out.toDataURL('image/png');
    emit('save', { file, dataUrl });
    emit('update:show', false);
  } finally {
    saving.value = false;
  }
}

function close() {
  emit('update:show', false);
}

const toolBtnClass = 'h-8 rounded px-2 text-xs transition hover:bg-[rgb(var(--primary-color)/0.12)] hover:text-[rgb(var(--primary-color))]';
const toolBtnActive = (t: Annotation['type']) => (selectedId.value && annotations.value.find(a => a.id === selectedId.value)?.type === t ? ' bg-[rgb(var(--primary-color)/0.12)] text-[rgb(var(--primary-color))]' : '');
</script>

<template>
  <NModal
    :show="props.show"
    preset="card"
    title="编辑图片"
    style="width: 820px"
    @update:show="(v: boolean) => (v ? undefined : close())"
  >
    <div class="flex flex-wrap items-center gap-2 mb-2">
      <NButton size="tiny" title="向左旋转 90°" @click="rotate(-90)">
        <template #icon><icon-mdi-rotate-left class="text-sm" /></template>
        左旋
      </NButton>
      <NButton size="tiny" title="向右旋转 90°" @click="rotate(90)">
        <template #icon><icon-mdi-rotate-right class="text-sm" /></template>
        右旋
      </NButton>
      <div class="mx-1 h-5 w-px bg-[var(--n-border-color)]"></div>
      <NButton size="tiny" :class="toolBtnClass + toolBtnActive('text')" @click="addAnnotation('text')">文字</NButton>
      <NButton size="tiny" :class="toolBtnClass + toolBtnActive('rect')" @click="addAnnotation('rect')">矩形</NButton>
      <NButton size="tiny" :class="toolBtnClass + toolBtnActive('circle')" @click="addAnnotation('circle')">圆形</NButton>
      <NButton size="tiny" :class="toolBtnClass + toolBtnActive('arrow')" @click="addAnnotation('arrow')">箭头</NButton>
      <div class="mx-1 h-5 w-px bg-[var(--n-border-color)]"></div>
      <NColorPicker v-model:value="annoColor" :show-alpha="false" size="small" :swatches="colorPresets" style="width: 120px" />
      <NSelect v-model:value="annoFontSize" :options="fontSizeOptions" size="small" style="width: 110px" />
      <label class="flex items-center gap-1 text-xs opacity-70">
        <input v-model="annoFill" type="checkbox" class="accent-[rgb(var(--primary-color))]" />
        填充
      </label>
      <div class="mx-1 h-5 w-px bg-[var(--n-border-color)]"></div>
      <NButton size="tiny" type="error" quaternary :disabled="!selectedId" @click="deleteSelected">删除标注</NButton>
      <NButton size="tiny" quaternary :disabled="!annotations.length" @click="clearAnnotations">清空</NButton>
    </div>

    <div ref="containerRef" class="relative w-full overflow-hidden rounded-lg bg-black" style="height: 430px">
      <CropperCanvas background class="cropper-canvas-host">
        <CropperImage :src="props.imageUrl" alt="待编辑图片"></CropperImage>
        <CropperSelection initial-coverage="0.8" outlined movable resizable></CropperSelection>
      </CropperCanvas>

      <!-- 标注层：整层不拦截事件，标注项自身可交互 -->
      <div
        class="annotation-layer absolute inset-0 z-10"
        @mousemove="onDragMove"
        @mouseup="onDragEnd"
        @mouseleave="onDragEnd"
      >
        <svg class="pointer-events-none absolute inset-0 h-full w-full">
          <template v-for="a in annotations" :key="a.id">
            <g v-if="a.type !== 'text'">
              <rect v-if="a.type === 'rect'" v-bind="annoShapeAttrs(a)" class="pointer-events-none" />
              <circle v-else-if="a.type === 'circle'" v-bind="annoShapeAttrs(a)" class="pointer-events-none" />
              <line v-else-if="a.type === 'arrow'" v-bind="annoShapeAttrs(a)" class="pointer-events-none" />
            </g>
          </template>
        </svg>
        <div
          v-for="a in annotations.filter(x => x.type === 'text')"
          :key="a.id"
          class="anno-text absolute max-w-[60%] cursor-move select-none leading-snug"
          :class="{ 'ring-1 ring-[rgb(var(--primary-color))]': selectedId === a.id }"
          :style="annoTextStyle(a)"
          @mousedown.stop="onDragStart(a, $event)"
          @dblclick.stop="startEditText(a)"
        >
          <template v-if="editingId === a.id">
            <NInput
              v-model:value="a.text"
              size="tiny"
              autofocus
              class="w-40 bg-black/60"
              @keydown.enter.prevent="commitEditText(a)"
              @blur="commitEditText(a)"
            />
          </template>
          <span v-else>{{ a.text }}</span>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between mt-3">
      <NRadioGroup :value="ratio" @update:value="setRatio">
        <NRadioButton v-for="opt in ratioOptions" :key="String(opt.value)" :value="opt.value">
          {{ opt.label }}
        </NRadioButton>
      </NRadioGroup>
      <span class="text-xs opacity-60">拖拽选区、滚轮缩放；建议先完成旋转/裁剪，再添加标注</span>
    </div>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="close">取消</NButton>
        <NButton type="primary" :loading="saving" @click="confirm">确认</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
.cropper-canvas-host {
  display: block;
  width: 100%;
  height: 100%;
}
.annotation-layer {
  pointer-events: none;
}
.anno-text {
  pointer-events: auto;
  text-shadow:
    0 1px 2px rgba(0, 0, 0, 0.6),
    0 0 3px rgba(0, 0, 0, 0.35);
  font-weight: 600;
  white-space: pre-wrap;
  min-width: 12px;
  min-height: 8px;
  background: transparent;
}
</style>
