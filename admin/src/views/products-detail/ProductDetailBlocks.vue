<script setup lang="ts">
import { ref, watch } from 'vue';
import { NButton, NFormItem, NInput, NSelect, NSpace, NTag } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import RichTextEditor from './RichTextEditor.vue';
import DetailBlockCanvas from './DetailBlockCanvas.vue';

/**
 * 商品结构化详情块编辑器（PRODUCT-DETAIL-BLOCKS）——画布式 WYSIWYG（方案 A）。
 *
 * 与后端 `ProductService.DETAIL_BLOCK_FIELDS` 白名单严格对齐：
 * rich_text(title/html/align) / image(title/images/caption) / image_text(title/image/html/layout)
 * / spec_table(title/columns/rows) / features(title/items) / faq(title/items) / video(title/url/poster)
 *
 * 交互范式（向 Shopify/Chewy 靠拢）：
 * - 画布容器模拟 C 端商品详情页宽度；每块在画布中渲染为 C 端最终效果（DetailBlockCanvas 与
 *   portal-web DetailBlocks.vue 同构、视觉对齐，编辑态即 C 端最终效果）
 * - 块外壳 hover 显示悬浮操作栏（上移/下移/类型切换/删除），点击块选中展开内联编辑面板
 * - 编辑面板复用各类型编辑控件：rich_text（Tiptap 内联 + Markdown）、features（逐行）、
 *   spec_table（悬浮层行列增删）、faq（卡片式 + 拖拽排序）
 */

type Block = Record<string, any>;

const props = defineProps<{ value: Block[] | null | undefined }>();
const emit = defineEmits<{
  (e: 'update:value', v: Block[]): void;
  (e: 'resources', ids: string[]): void;
}>();

/** 已登记/上传的资源 ID（供父级保存时 syncRefs 追引用） */
const registeredResourceIds = ref<string[]>([]);

function collectResource(item: any): void {
  const id = item?.id;
  if (!id) return;
  if (!registeredResourceIds.value.includes(id)) {
    registeredResourceIds.value = [...registeredResourceIds.value, id];
    emit('resources', registeredResourceIds.value);
  }
}

const typeOptions = [
  { label: '富文本', value: 'rich_text' },
  { label: '图片', value: 'image' },
  { label: '图文', value: 'image_text' },
  { label: '规格表', value: 'spec_table' },
  { label: '卖点列表', value: 'features' },
  { label: 'FAQ', value: 'faq' },
  { label: '视频', value: 'video' }
];

const alignOptions = [
  { label: '左对齐', value: 'left' },
  { label: '居中', value: 'center' },
  { label: '右对齐', value: 'right' }
];

const layoutOptions = [
  { label: '左图右文', value: 'left' },
  { label: '左文右图', value: 'right' }
];

const hintMap: Record<string, string> = {
  image: '每行一个图片 URL',
  faq: '一张卡片一对问答，问题与答案分栏填写'
};

const local = ref<Block[]>([]);
const drafts = ref<Record<string, string>>({});

/** 当前选中编辑的块下标（-1 = 无选中，全部渲染态） */
const selectedIdx = ref(-1);

function toggleSelect(i: number): void {
  selectedIdx.value = selectedIdx.value === i ? -1 : i;
}

/** 富文本编辑器内联展开（块下标） */
const richEditor = ref<{ show: boolean; idx: number }>({ show: false, idx: -1 });

/** 卖点：一行一条（块下标 -> 字符串数组草稿） */
const featDrafts = ref<Record<number, string[]>>({});

/** 规格表：列头与单元格草稿（块下标 -> { cols: string[]; rows: { id: number; cells: string[] }[] }） */
const specDrafts = ref<Record<number, { cols: string[]; rows: { id: number; cells: string[] }[] }>>({});

/** FAQ：一张卡片一对问答（块下标 -> 卡片草稿数组） */
const faqDrafts = ref<Record<number, { id: number; question: string; answer: string }[]>>({});
let faqRowSeq = 0;
/** 拖拽排序进行中标记：拖拽期间挂起 faqCommit，避免输入框 blur 触发 commit 打断排序 */
let faqDragging = false;

function faqDragStart(): void {
  faqDragging = true;
}

function faqDragEnd(i: number): void {
  faqDragging = false;
  faqCommit(i);
}

let specRowSeq = 0;

function clone(v: any): Block[] {
  return JSON.parse(JSON.stringify(v ?? []));
}

function typeLabel(type: string): string {
  return typeOptions.find(o => o.value === type)?.label || type;
}

// 外部值变化时同步到本地副本；内容一致则不重置，避免打断编辑
watch(
  () => props.value,
  v => {
    const next = clone(v);
    if (JSON.stringify(next) === JSON.stringify(local.value)) return;
    local.value = next;
    selectedIdx.value = -1;
    drafts.value = {};
    featDrafts.value = {};
    specDrafts.value = {};
    faqDrafts.value = {};
  },
  { immediate: true, deep: true }
);

// 本地编辑回写父级（父级若回写同内容，上面的 watch 会因内容一致而跳过，不会循环）
watch(
  local,
  () => {
    emit('update:value', clone(local.value));
  },
  { deep: true }
);

function add(): void {
  local.value.push({ type: 'rich_text', title: '' });
}

function remove(i: number): void {
  local.value.splice(i, 1);
  if (selectedIdx.value === i) selectedIdx.value = -1;
  else if (selectedIdx.value > i) selectedIdx.value -= 1;
  drafts.value = {};
  featDrafts.value = {};
  specDrafts.value = {};
  faqDrafts.value = {};
}

function move(i: number, delta: number): void {
  const j = i + delta;
  if (j < 0 || j >= local.value.length) return;
  const arr = local.value;
  const tmp = arr[i];
  arr[i] = arr[j];
  arr[j] = tmp;
  if (selectedIdx.value === i) selectedIdx.value = j;
  else if (selectedIdx.value === j) selectedIdx.value = i;
  drafts.value = {};
  faqDrafts.value = {};
}

function changeType(i: number, type: string): void {
  const title = local.value[i]?.title;
  local.value[i] = { type, ...(title ? { title } : {}) };
  drafts.value = {};
  faqDrafts.value = {};
}

/* ---------------- 富文本 ---------------- */

function openRichEditor(i: number) {
  richEditor.value = { show: true, idx: i };
}

function saveRichHtml(html: string) {
  const i = richEditor.value.idx;
  if (i >= 0 && local.value[i]) local.value[i].html = html;
  richEditor.value = { show: false, idx: -1 };
}

function clearRichHtml(i: number): void {
  if (local.value[i]) local.value[i].html = '';
}

/* ---------------- 卖点：一行一条 ---------------- */

function featItems(i: number): string[] {
  const d = featDrafts.value[i];
  if (d) return d;
  const items = local.value[i]?.items;
  const arr = Array.isArray(items)
    ? items.map((x: any) => {
        if (x && typeof x === 'object') {
          return String(x.label ?? x.value ?? x.text ?? '');
        }
        return String(x ?? '');
      })
    : [];
  featDrafts.value[i] = arr;
  return arr;
}

function featAdd(i: number) {
  const arr = featItems(i);
  arr.push('');
  featDrafts.value[i] = [...arr];
}

function featRemove(i: number, j: number) {
  const arr = featItems(i);
  arr.splice(j, 1);
  featDrafts.value[i] = [...arr];
}

function featCommit(i: number) {
  const arr = (featDrafts.value[i] || []).map(s => s.trim()).filter(Boolean);
  if (local.value[i]) local.value[i].items = arr;
  Reflect.deleteProperty(featDrafts.value, i);
}

/* ---------------- 规格表：轻量表格 ---------------- */

function specState(i: number): { cols: string[]; rows: { id: number; cells: string[] }[] } {
  const d = specDrafts.value[i];
  if (d) return d;
  const block = local.value[i] || {};
  const rawCols: string[] = Array.isArray(block.columns) ? block.columns.map(c => String(c ?? '').trim()) : [];
  const keep = rawCols.map(c => c !== '');
  const cols = rawCols.filter(c => c !== '');
  if (cols.length === 0) cols.push('名称');
  if (cols.length === 1) cols.push('值');
  const rows = Array.isArray(block.rows)
    ? block.rows.map((r: any) => {
        const cells = r && typeof r === 'object' ? Object.values(r).map(v => String(v ?? '')) : [String(r ?? ''), ''];
        const kept = cells.filter((_, j) => keep[j]);
        while (kept.length < cols.length) kept.push('');
        return { id: ++specRowSeq, cells: kept.slice(0, cols.length) };
      })
    : [];
  specDrafts.value[i] = { cols, rows };
  return specDrafts.value[i];
}

function specAddCol(i: number) {
  const s = specState(i);
  s.cols.push(`列 ${s.cols.length + 1}`);
  s.rows.forEach(r => r.cells.push(''));
  specDrafts.value[i] = { ...s };
}

function specInsertCol(i: number, j: number) {
  const s = specState(i);
  s.cols.splice(j + 1, 0, `列 ${s.cols.length + 1}`);
  s.rows.forEach(r => r.cells.splice(j + 1, 0, ''));
  specDrafts.value[i] = { ...s };
}

function specRemoveCol(i: number, j: number) {
  const s = specState(i);
  if (s.cols.length <= 2) return;
  s.cols.splice(j, 1);
  s.rows.forEach(r => r.cells.splice(j, 1));
  specDrafts.value[i] = { ...s };
}

function specAddRow(i: number) {
  const s = specState(i);
  s.rows.push({ id: ++specRowSeq, cells: s.cols.map(() => '') });
  specDrafts.value[i] = { ...s };
}

function specInsertRow(i: number, r: number) {
  const s = specState(i);
  s.rows.splice(r + 1, 0, { id: ++specRowSeq, cells: s.cols.map(() => '') });
  specDrafts.value[i] = { ...s };
}

function specRemoveRow(i: number, j: number) {
  const s = specState(i);
  s.rows.splice(j, 1);
  specDrafts.value[i] = { ...s };
}

function specCommit(i: number) {
  const s = specDrafts.value[i];
  if (!s || !local.value[i]) return;
  const keep: boolean[] = s.cols.map(c => c.trim() !== '');
  const cols = s.cols.map(c => c.trim()).filter(Boolean);
  if (cols.length === 0) cols.push('名称');
  if (cols.length === 1) cols.push('值');
  const rows = s.rows
    .map(r => {
      const cells = r.cells.map((c, j) => (keep[j] ? c.trim() : null)).filter((c): c is string => c !== null);
      while (cells.length < cols.length) cells.push('');
      return { id: r.id, cells: cells.slice(0, cols.length) };
    })
    .filter(r => r.cells.some(Boolean))
    .map(r => {
      const obj: Record<string, string> = {};
      r.cells.forEach((cell, j) => {
        obj[cols[j] || `col${j}`] = cell;
      });
      return obj;
    });
  local.value[i].columns = cols.length ? cols : undefined;
  local.value[i].rows = rows;
  Reflect.deleteProperty(specDrafts.value, i);
}

/* ---------------- FAQ：一张卡片一对问答 ---------------- */

function faqState(i: number): { id: number; question: string; answer: string }[] {
  const d = faqDrafts.value[i];
  if (d) return d;
  const block = local.value[i] || {};
  const items = Array.isArray(block.items) ? block.items : [];
  const arr = items.map((x: any) => {
    const obj = x && typeof x === 'object' ? x : { question: String(x ?? ''), answer: '' };
    return { id: ++faqRowSeq, question: String(obj.question ?? ''), answer: String(obj.answer ?? '') };
  });
  faqDrafts.value[i] = arr;
  return arr;
}

function faqAdd(i: number): void {
  const arr = faqState(i);
  arr.push({ id: ++faqRowSeq, question: '', answer: '' });
  faqDrafts.value[i] = [...arr];
}

function faqRemove(i: number, j: number): void {
  const arr = faqState(i);
  arr.splice(j, 1);
  faqDrafts.value[i] = [...arr];
}

function faqCommit(i: number): void {
  if (faqDragging) return;
  const arr = (faqDrafts.value[i] || [])
    .map(x => ({ question: x.question.trim(), answer: x.answer.trim() }))
    .filter(x => x.question !== '' || x.answer !== '');
  if (local.value[i]) local.value[i].items = arr;
  Reflect.deleteProperty(faqDrafts.value, i);
}
</script>

<template>
  <div>
    <div class="mb-2 text-xs opacity-60">
      画布预览与 C 端商品详情页渲染一致；点击块展开编辑，悬停块显示操作栏
    </div>

    <div v-if="local.length" class="canvas-shell">
      <div
        v-for="(block, i) in local"
        :key="i"
        class="canvas-block"
        :class="{ 'canvas-block-active': selectedIdx === i }"
        @click="toggleSelect(i)"
      >
        <!-- 悬浮操作栏（hover / 选中时显示） -->
        <div class="canvas-ops" @click.stop>
          <NSpace size="small" align="center" :wrap="false">
            <NTag size="small" type="info">{{ i + 1 }} · {{ typeLabel(block.type) }}</NTag>
            <NSelect
              size="tiny"
              style="width: 120px"
              :value="block.type"
              :options="typeOptions"
              @update:value="(v: string) => changeType(i, v)"
            />
            <NButton size="tiny" :disabled="i === 0" @click="move(i, -1)">上移</NButton>
            <NButton size="tiny" :disabled="i === local.length - 1" @click="move(i, 1)">下移</NButton>
            <NButton size="tiny" type="error" @click="remove(i)">删除</NButton>
          </NSpace>
        </div>

        <!-- 画布渲染（C 端同构，编辑态即最终效果） -->
        <DetailBlockCanvas v-if="selectedIdx !== i" :block="block" />

        <!-- 编辑面板（选中展开） -->
        <div v-else class="canvas-edit-panel" @click.stop>
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs font-medium opacity-70">编辑「{{ typeLabel(block.type) }}」</span>
            <NButton size="tiny" quaternary type="primary" @click="selectedIdx = -1">完成</NButton>
          </div>

          <NFormItem label="块标题" :show-feedback="false">
            <NInput v-model:value="block.title" placeholder="可选，用于详情页小标题" />
          </NFormItem>

          <!-- 富文本：Tiptap + Markdown 双模式内联编辑 -->
          <template v-if="block.type === 'rich_text'">
            <RichTextEditor
              v-if="richEditor.show && richEditor.idx === i"
              inline
              :show="true"
              :html="block.html || ''"
              :title="block.title || ''"
              @update:show="(v: boolean) => (v ? undefined : (richEditor = { show: false, idx: -1 }))"
              @save="saveRichHtml"
              @register="collectResource"
            />
            <template v-else>
              <NFormItem label="对齐" :show-feedback="false">
                <NSelect v-model:value="block.align" :options="alignOptions" style="width: 160px" clearable />
              </NFormItem>
              <div class="mt-2 flex items-center justify-end gap-2 border-t border-[var(--n-border-color)] pt-2">
                <NButton size="small" type="primary" quaternary @click="openRichEditor(i)">富文本编辑</NButton>
                <NButton v-if="block.html" size="small" quaternary type="error" @click="clearRichHtml(i)">清空</NButton>
              </div>
            </template>
          </template>

          <!-- 图片 -->
          <template v-else-if="block.type === 'image'">
            <NFormItem label="图片（支持多张）" :show-feedback="false">
              <ResourceInput v-model="block.images" type="image" multiple @register="collectResource" />
            </NFormItem>
            <NFormItem label="图片说明" :show-feedback="false">
              <NInput v-model:value="block.caption" />
            </NFormItem>
          </template>

          <!-- 图文 -->
          <template v-else-if="block.type === 'image_text'">
            <NFormItem label="图片" :show-feedback="false">
              <ResourceInput v-model="block.image" type="image" @register="collectResource" />
            </NFormItem>
            <NFormItem label="正文（支持简单 HTML）" :show-feedback="false">
              <NInput v-model:value="block.html" type="textarea" :rows="3" />
            </NFormItem>
            <NFormItem label="版式" :show-feedback="false">
              <NSelect v-model:value="block.layout" :options="layoutOptions" style="width: 160px" clearable />
            </NFormItem>
          </template>

          <!-- 规格表：所见即所得表格编辑 -->
          <template v-else-if="block.type === 'spec_table'">
            <div class="overflow-x-auto">
              <table class="spec-table w-full border-collapse text-sm">
                <thead>
                  <tr>
                    <th
                      v-for="(col, j) in specState(i).cols"
                      :key="j"
                      class="relative border border-[var(--n-border-color)] bg-gray-100 p-1 align-middle"
                    >
                      <NInput
                        v-model:value="specState(i).cols[j]"
                        :bordered="false"
                        size="small"
                        placeholder="列名"
                        @blur="specCommit(i)"
                      />
                      <NSpace size="small" :wrap="false" class="spec-col-ops">
                        <NButton
                          size="tiny"
                          quaternary
                          type="primary"
                          title="在该列右侧插入列"
                          @click="
                            specInsertCol(i, j);
                            specCommit(i);
                          "
                        >
                          ＋
                        </NButton>
                        <NButton
                          size="tiny"
                          quaternary
                          type="error"
                          title="删除该列"
                          :disabled="specState(i).cols.length <= 2"
                          @click="
                            specRemoveCol(i, j);
                            specCommit(i);
                          "
                        >
                          −
                        </NButton>
                      </NSpace>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="(row, r) in specState(i).rows" :key="row.id">
                    <tr class="spec-data-row">
                      <td
                        v-for="(cell, c) in row.cells"
                        :key="c"
                        class="relative border border-[var(--n-border-color)] p-1 align-middle"
                      >
                        <NInput
                          v-model:value="row.cells[c]"
                          :bordered="false"
                          size="small"
                          placeholder="值"
                          @blur="specCommit(i)"
                        />
                        <NSpace
                          v-if="c === row.cells.length - 1"
                          size="small"
                          :wrap="false"
                          justify="center"
                          class="spec-row-ops"
                        >
                          <NButton
                            size="tiny"
                            quaternary
                            type="primary"
                            title="在该行下方插入行"
                            @click="specInsertRow(i, r)"
                          >
                            ＋
                          </NButton>
                          <NButton
                            size="tiny"
                            quaternary
                            type="error"
                            title="删除该行"
                            @click="
                              specRemoveRow(i, r);
                              specCommit(i);
                            "
                          >
                            −
                          </NButton>
                        </NSpace>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
            <NSpace size="small" class="mt-2">
              <NButton
                size="tiny"
                dashed
                @click="
                  specAddCol(i);
                  specCommit(i);
                "
              >
                + 添加列
              </NButton>
              <NButton size="tiny" dashed @click="specAddRow(i)">+ 添加行</NButton>
              <span class="text-xs opacity-60">
                表头可直接改列名；悬停表头行末显示 ＋/− 增删列，悬停数据行右侧悬浮 ＋/− 增删行
              </span>
            </NSpace>
          </template>

          <!-- 卖点：一行一条 -->
          <template v-else-if="block.type === 'features'">
            <div class="flex flex-col gap-1 mb-2">
              <div v-for="(item, j) in featItems(i)" :key="j" class="flex items-center gap-2">
                <span class="w-4 text-center text-xs opacity-40">{{ j + 1 }}</span>
                <NInput
                  v-model:value="featItems(i)[j]"
                  placeholder="一条卖点，如：无谷物配方，易消化"
                  @blur="featCommit(i)"
                />
                <NButton
                  size="tiny"
                  quaternary
                  type="error"
                  @click="
                    featRemove(i, j);
                    featCommit(i);
                  "
                >
                  删除
                </NButton>
              </div>
            </div>
            <NSpace size="small">
              <NButton size="tiny" dashed @click="featAdd(i)">+ 添加卖点</NButton>
              <span class="text-xs opacity-60">一行一条，C 端渲染为要点列表</span>
            </NSpace>
          </template>

          <!-- FAQ：一张卡片一对问答 -->
          <template v-else-if="block.type === 'faq'">
            <NFormItem :label="hintMap.faq" :show-feedback="false" class="faq-editor">
              <NSpace size="small" class="mb-2">
                <NButton size="tiny" dashed @click="faqAdd(i)">+ 添加问答</NButton>
                <span class="text-xs opacity-60">拖动 ⠿ 调整顺序，C 端按此顺序展示</span>
              </NSpace>
              <VueDraggable
                v-if="faqState(i).length >= 0"
                v-model="faqDrafts[i]"
                item-key="id"
                handle=".faq-drag-handle"
                class="faq-list flex flex-row flex-wrap gap-2 mb-2"
                ghost-class="faq-ghost"
                :animation="150"
                @start="faqDragStart"
                @end="faqDragEnd(i)"
              >
                <div v-for="(item, j) in faqState(i)" :key="item.id" class="faq-card">
                  <div class="flex items-center justify-between mb-1">
                    <span class="faq-drag-handle" title="拖动调整顺序">⠿</span>
                    <span class="text-xs opacity-40">Q{{ j + 1 }}</span>
                    <NButton
                      size="tiny"
                      quaternary
                      type="error"
                      title="删除该问答"
                      @click="
                        faqRemove(i, j);
                        faqCommit(i);
                      "
                    >
                      −
                    </NButton>
                  </div>
                  <NInput
                    v-model:value="faqState(i)[j].question"
                    placeholder="问题，如：这款猫粮适合幼猫吗？"
                    @blur="faqCommit(i)"
                  />
                  <NInput
                    v-model:value="faqState(i)[j].answer"
                    type="textarea"
                    :rows="2"
                    placeholder="答案"
                    class="mt-1"
                    @blur="faqCommit(i)"
                  />
                </div>
              </VueDraggable>
            </NFormItem>
          </template>

          <!-- 视频 -->
          <template v-else-if="block.type === 'video'">
            <NFormItem label="视频" :show-feedback="false">
              <ResourceInput
                v-model="block.url"
                type="video"
                placeholder="粘贴视频 URL，如 https://.../demo.mp4"
                @register="collectResource"
              />
            </NFormItem>
            <NFormItem label="封面图" :show-feedback="false">
              <ResourceInput v-model="block.poster" type="image" @register="collectResource" />
            </NFormItem>
          </template>
        </div>
      </div>
    </div>
    <NEmpty v-else description="暂无详情块，仅使用上方简介" size="small" class="py-3" />

    <NSpace size="small" class="mt-2">
      <NButton dashed size="small" @click="add">+ 添加详情块</NButton>
      <span class="text-xs opacity-60 self-center">最多 50 块；与简介互补，详情页按顺序渲染</span>
    </NSpace>
  </div>
</template>

<style scoped>
/* ===== 画布容器：模拟 C 端详情页宽度与留白 ===== */
.canvas-shell {
  border: 1px dashed rgba(128, 128, 128, 0.35);
  border-radius: 8px;
  padding: 16px;
  background: #fafafa;
}

/* ===== 块外壳：选中态高亮，hover 显示操作栏 ===== */
.canvas-block {
  position: relative;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid rgba(128, 128, 128, 0.18);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  cursor: pointer;
}
.canvas-block:last-child {
  margin-bottom: 0;
}
.canvas-block:hover {
  border-color: rgba(0, 0, 0, 0.35);
}
.canvas-block-active {
  border-color: var(--n-color-primary);
  box-shadow: 0 0 0 1px var(--n-color-primary);
}

/* ===== 悬浮操作栏：不占块内空间，hover/选中时淡入 ===== */
.canvas-ops {
  position: absolute;
  top: -15px;
  right: 8px;
  z-index: 10;
  display: flex;
  align-items: center;
  background: #fff;
  border: 1px solid rgba(128, 128, 128, 0.25);
  border-radius: 6px;
  padding: 2px 6px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}
.canvas-block:hover .canvas-ops,
.canvas-block-active .canvas-ops {
  opacity: 1;
  pointer-events: auto;
}

/* ===== 编辑面板：渲染态与编辑态分隔线 ===== */
.canvas-edit-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(128, 128, 128, 0.3);
}

/* ===== FAQ 编辑区 ===== */
.faq-editor :deep(.n-form-item-blank) {
  flex-direction: column;
  align-items: stretch;
}
.faq-list {
  align-items: stretch;
}
.faq-card {
  flex: 1 1 280px;
  min-width: 240px;
  max-width: 400px;
  border: 1px solid rgba(128, 128, 128, 0.24);
  border-radius: 6px;
  padding: 8px 10px;
  background: rgba(128, 128, 128, 0.04);
}
.faq-drag-handle {
  cursor: grab;
  color: rgba(128, 128, 128, 0.5);
  font-size: 12px;
  line-height: 1;
  user-select: none;
}
.faq-drag-handle:active {
  cursor: grabbing;
}
.faq-ghost {
  opacity: 0.4;
  border-style: dashed;
}

/* ===== 规格表编辑：悬浮层行列增删 ===== */
.spec-table th,
.spec-table td {
  text-align: center;
}
.spec-table th .n-input__input-el,
.spec-table td .n-input__input-el {
  text-align: center;
}
.spec-row-ops {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  opacity: 0;
  transition: opacity 0.15s ease;
  pointer-events: none;
}
.spec-data-row:hover .spec-row-ops {
  opacity: 1;
  pointer-events: auto;
}
.spec-row-ops .n-button {
  border: none;
}
.spec-col-ops {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  opacity: 0;
  transition: opacity 0.15s ease;
  pointer-events: none;
}
.spec-table thead:hover .spec-col-ops {
  opacity: 1;
  pointer-events: auto;
}
.spec-col-ops .n-button {
  border: none;
}
</style>
