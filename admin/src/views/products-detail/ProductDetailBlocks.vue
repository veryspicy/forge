<script setup lang="ts">
import { ref, watch } from 'vue';
import { NButton, NFormItem, NInput, NSelect, NSpace, NTag } from 'naive-ui';
import RichTextEditor from './RichTextEditor.vue';

/**
 * 商品结构化详情块编辑器（PRODUCT-DETAIL-BLOCKS）。
 *
 * 与后端 `ProductService.DETAIL_BLOCK_FIELDS` 白名单严格对齐：
 * rich_text(title/html/align) / image(title/images/caption) / image_text(title/image/html/layout)
 * / spec_table(title/columns/rows) / features(title/items) / faq(title/items) / video(title/url/poster)
 *
 * 交互升级（向 Shopify/Chewy 靠拢）：
 * - rich_text：富文本 Tiptap 所见即所得 + Markdown 源码双模式（RichTextEditor.vue）
 * - features：卖点一行一条，逐行编辑
 * - spec_table：轻量表格编辑（列头 + 单元格，支持多列）
 */

type Block = Record<string, any>;

const props = defineProps<{ value: Block[] | null | undefined }>();
const emit = defineEmits<{ (e: 'update:value', v: Block[]): void }>();

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
  faq: '每行 `问题|答案`'
};

const local = ref<Block[]>([]);
const drafts = ref<Record<string, string>>({});

/** 富文本编辑器弹窗 */
const richEditor = ref<{ show: boolean; idx: number }>({ show: false, idx: -1 });

/** 卖点：一行一条（块下标 -> 字符串数组草稿） */
const featDrafts = ref<Record<number, string[]>>({});

/** 规格表：列头与单元格草稿（块下标 -> { cols: string[]; rows: { id: number; cells: string[] }[] }） */
const specDrafts = ref<Record<number, { cols: string[]; rows: { id: number; cells: string[] }[] }>>({});

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
    drafts.value = {};
    featDrafts.value = {};
    specDrafts.value = {};
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

function dkey(i: number, k: string): string {
  return `${i}:${k}`;
}

function arrText(i: number, k: string): string {
  const draft = drafts.value[dkey(i, k)];
  if (draft !== undefined) return draft;
  const v = (local.value[i] || {})[k];
  if (!Array.isArray(v)) return '';
  return v.map((x: any) => (typeof x === 'string' ? x : rowToText(x))).join('\n');
}

function setDraft(i: number, k: string, text: string): void {
  drafts.value = { ...drafts.value, [dkey(i, k)]: text };
}

function commitDraft(i: number, k: string): void {
  const key = dkey(i, k);
  const text = drafts.value[key];
  if (text === undefined) return;
  const lines = text
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean);
  const block = local.value[i] || {};
  let parsed: any[];
  if (k === 'items' && block.type === 'faq') {
    parsed = lines.map(line => {
      const idx = line.indexOf('|');
      return idx === -1
        ? { question: line, answer: '' }
        : { question: line.slice(0, idx).trim(), answer: line.slice(idx + 1).trim() };
    });
  } else {
    parsed = lines;
  }
  block[k] = parsed;
  drafts.value = Object.fromEntries(Object.entries(drafts.value).filter(([draftKey]) => draftKey !== key));
}

function rowToText(x: any): string {
  if (x && typeof x === 'object') {
    if ('question' in x || 'answer' in x) return `${x.question ?? ''}|${x.answer ?? ''}`;
    if ('label' in x || 'value' in x) return `${x.label ?? ''}=${x.value ?? ''}`;
    return Object.values(x).join(' | ');
  }
  return String(x ?? '');
}

function add(): void {
  local.value.push({ type: 'rich_text', title: '' });
}

function remove(i: number): void {
  local.value.splice(i, 1);
  drafts.value = {};
  featDrafts.value = {};
  specDrafts.value = {};
}

function move(i: number, delta: number): void {
  const j = i + delta;
  if (j < 0 || j >= local.value.length) return;
  const arr = local.value;
  const tmp = arr[i];
  arr[i] = arr[j];
  arr[j] = tmp;
  drafts.value = {};
}

function changeType(i: number, type: string): void {
  const title = local.value[i]?.title;
  local.value[i] = { type, ...(title ? { title } : {}) };
  drafts.value = {};
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

function stripHtmlForPreview(html: string): string {
  if (!html) return '';
  const div = document.createElement('div');
  div.innerHTML = html;
  return (div.textContent || '').trim().slice(0, 120);
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
  const cols = Array.isArray(block.columns) && block.columns.length ? [...block.columns] : ['名称', '值'];
  const rows = Array.isArray(block.rows)
    ? block.rows.map((r: any) => {
        const cells = r && typeof r === 'object' ? Object.values(r).map(v => String(v ?? '')) : [String(r ?? ''), ''];
        while (cells.length < cols.length) cells.push('');
        return { id: ++specRowSeq, cells: cells.slice(0, cols.length) };
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
  const cols = s.cols.map(c => c.trim()).filter(Boolean);
  const rows = s.rows
    .map(r => r.cells.map(c => c.trim()))
    .filter(r => r.some(Boolean))
    .map(r => {
      const obj: Record<string, string> = {};
      r.forEach((cell, j) => {
        obj[cols[j] || `col${j}`] = cell;
      });
      return obj;
    });
  local.value[i].columns = cols.length ? cols : undefined;
  local.value[i].rows = rows;
  Reflect.deleteProperty(specDrafts.value, i);
}
</script>

<template>
  <div>
    <div v-if="local.length" class="flex flex-col gap-3 mb-3">
      <div
        v-for="(block, i) in local"
        :key="i"
        class="rounded-md border border-[var(--n-border-color)] p-3"
      >
        <div class="flex items-center justify-between gap-2 mb-2">
          <NSpace size="small" align="center">
            <NTag size="small" type="info">{{ i + 1 }} · {{ typeLabel(block.type) }}</NTag>
            <NSelect
              size="small"
              style="width: 130px"
              :value="block.type"
              :options="typeOptions"
              @update:value="(v: string) => changeType(i, v)"
            />
          </NSpace>
          <NSpace size="small">
            <NButton size="tiny" :disabled="i === 0" @click="move(i, -1)">上移</NButton>
            <NButton size="tiny" :disabled="i === local.length - 1" @click="move(i, 1)">下移</NButton>
            <NButton size="tiny" type="error" @click="remove(i)">删除</NButton>
          </NSpace>
        </div>

        <NFormItem label="块标题" :show-feedback="false">
          <NInput v-model:value="block.title" placeholder="可选，用于详情页小标题" />
        </NFormItem>

        <!-- 富文本：Tiptap + Markdown -->
        <template v-if="block.type === 'rich_text'">
          <div class="flex items-center justify-between gap-2">
            <div class="text-sm opacity-80">
              {{ block.html ? (stripHtmlForPreview(block.html) + '…') : '（空）' }}
            </div>
            <NSpace size="small">
              <NButton size="small" type="primary" quaternary @click="openRichEditor(i)">富文本编辑</NButton>
              <NButton
                v-if="block.html"
                size="small"
                quaternary
                @click="block.html = ''"
              >
                清空
              </NButton>
            </NSpace>
          </div>
          <NFormItem label="对齐" :show-feedback="false" class="mt-2">
            <NSelect v-model:value="block.align" :options="alignOptions" style="width: 160px" clearable />
          </NFormItem>
        </template>

        <!-- 图片 -->
        <template v-else-if="block.type === 'image'">
          <NFormItem :label="hintMap.image" :show-feedback="false">
            <NInput
              type="textarea"
              :rows="3"
              :value="arrText(i, 'images')"
              @update:value="(v: string) => setDraft(i, 'images', v)"
              @blur="commitDraft(i, 'images')"
            />
          </NFormItem>
          <NFormItem label="图片说明" :show-feedback="false">
            <NInput v-model:value="block.caption" />
          </NFormItem>
        </template>

        <!-- 图文 -->
        <template v-else-if="block.type === 'image_text'">
          <NFormItem label="图片 URL" :show-feedback="false">
            <NInput v-model:value="block.image" placeholder="https://..." />
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
            <table class="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th
                    v-for="(col, j) in specState(i).cols"
                    :key="j"
                    class="border border-[var(--n-border-color)] bg-gray-100 p-1 align-middle"
                  >
                    <div class="flex items-center gap-1">
                      <NInput
                        v-model:value="specState(i).cols[j]"
                        :bordered="false"
                        size="small"
                        placeholder="列名"
                        @blur="specCommit(i)"
                      />
                      <NButton
                        size="tiny"
                        quaternary
                        type="primary"
                        title="在该列右侧插入列"
                        @click="specInsertCol(i, j); specCommit(i)"
                      >
                        ＋
                      </NButton>
                      <NButton
                        size="tiny"
                        quaternary
                        type="error"
                        title="删除该列"
                        :disabled="specState(i).cols.length <= 2"
                        @click="specRemoveCol(i, j); specCommit(i)"
                      >
                        −
                      </NButton>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <template v-for="(row, r) in specState(i).rows" :key="row.id">
                  <tr class="spec-data-row">
                    <td
                      v-for="(cell, c) in row.cells"
                      :key="c"
                      class="border border-[var(--n-border-color)] p-1 align-middle"
                    >
                      <NInput
                        v-model:value="row.cells[c]"
                        :bordered="false"
                        size="small"
                        placeholder="值"
                        @blur="specCommit(i)"
                      />
                    </td>
                  </tr>
                  <tr class="spec-row-ops">
                    <td
                      :colspan="specState(i).cols.length"
                      class="spec-row-ops-cell"
                    >
                      <NSpace size="small" :wrap="false" class="spec-row-ops-btns">
                        <NButton
                          size="tiny"
                          quaternary
                          type="primary"
                          title="在该行下方插入行"
                          @click="specInsertRow(i, r); specCommit(i)"
                        >
                          ＋
                        </NButton>
                        <NButton
                          size="tiny"
                          quaternary
                          type="error"
                          title="删除该行"
                          @click="specRemoveRow(i, r); specCommit(i)"
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
            <NButton size="tiny" dashed @click="specAddCol(i); specCommit(i)">+ 添加列</NButton>
            <NButton size="tiny" dashed @click="specAddRow(i)">+ 添加行</NButton>
            <span class="text-xs opacity-60">表头可直接改列名，列头 ＋/− 增删列；鼠标移到行间边框出现 ＋/− 增删行</span>
          </NSpace>
        </template>

        <!-- 卖点：一行一条 -->
        <template v-else-if="block.type === 'features'">
          <div class="flex flex-col gap-1 mb-2">
            <div v-for="(item, j) in featItems(i)" :key="j" class="flex items-center gap-2">
              <span class="w-4 text-center text-xs opacity-40">{{ j + 1 }}</span>
              <NInput v-model:value="featItems(i)[j]" placeholder="一条卖点，如：无谷物配方，易消化" @blur="featCommit(i)" />
              <NButton size="tiny" quaternary type="error" @click="featRemove(i, j); featCommit(i)">删除</NButton>
            </div>
          </div>
          <NSpace size="small">
            <NButton size="tiny" dashed @click="featAdd(i)">+ 添加卖点</NButton>
            <span class="text-xs opacity-60">一行一条，C 端渲染为要点列表</span>
          </NSpace>
        </template>

        <!-- FAQ -->
        <template v-else-if="block.type === 'faq'">
          <NFormItem :label="hintMap.faq" :show-feedback="false">
            <NInput
              type="textarea"
              :rows="4"
              :value="arrText(i, 'items')"
              @update:value="(v: string) => setDraft(i, 'items', v)"
              @blur="commitDraft(i, 'items')"
            />
          </NFormItem>
        </template>

        <!-- 视频 -->
        <template v-else-if="block.type === 'video'">
          <NFormItem label="视频 URL" :show-feedback="false">
            <NInput v-model:value="block.url" placeholder="https://.../demo.mp4" />
          </NFormItem>
          <NFormItem label="封面图 URL" :show-feedback="false">
            <NInput v-model:value="block.poster" />
          </NFormItem>
        </template>
      </div>
    </div>
    <NEmpty v-else description="暂无详情块，仅使用上方简介" size="small" class="py-3" />

    <NSpace size="small" class="mt-2">
      <NButton dashed size="small" @click="add">+ 添加详情块</NButton>
      <span class="text-xs opacity-60 self-center">最多 50 块；与简介互补，详情页按顺序渲染</span>
    </NSpace>

    <RichTextEditor
      :show="richEditor.show"
      :html="richEditor.idx >= 0 ? local[richEditor.idx]?.html || '' : ''"
      :title="richEditor.idx >= 0 ? local[richEditor.idx]?.title || '' : ''"
      @update:show="(v: boolean) => (v ? undefined : (richEditor = { show: false, idx: -1 }))"
      @save="saveRichHtml"
    />
  </div>
</template>

<style scoped>
/* 规格表：行操作条默认隐藏，仅当鼠标悬停到上一数据行或行间轨道时显示 */
.spec-row-ops {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}
.spec-data-row:hover + .spec-row-ops,
.spec-row-ops:hover {
  opacity: 1;
  pointer-events: auto;
}
.spec-row-ops-cell {
  height: 8px;
  padding: 0;
  position: relative;
  border: none;
}
.spec-row-ops-btns {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
}
</style>
