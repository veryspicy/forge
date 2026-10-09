<script setup lang="ts">
import { ref, watch } from 'vue';
import { NButton, NFormItem, NInput, NSelect, NSpace, NTag } from 'naive-ui';

/**
 * 商品结构化详情块编辑器（PRODUCT-DETAIL-BLOCKS）。
 *
 * 与后端 `ProductService.DETAIL_BLOCK_FIELDS` 白名单严格对齐：
 * rich_text(title/html/align) / image(title/images/caption) / image_text(title/image/html/layout)
 * / spec_table(title/columns/rows) / features(title/items) / faq(title/items) / video(title/url/poster)
 *
 * 数组类字段用「每行一条」的文本域编辑，失焦时解析回结构化数组：
 * - items(FAQ) 每行 `问题|答案`
 * - rows 每行 `名称=值`
 * - images / columns / features.items 每行一条
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
  spec_table: '每行 `名称=值`，如：尺寸=12cm',
  features: '每行一条卖点',
  faq: '每行 `问题|答案`',
  columns: '每行一个列名，可留空'
};

const local = ref<Block[]>([]);
const drafts = ref<Record<string, string>>({});

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

function rowToText(x: any): string {
  if (x && typeof x === 'object') {
    if ('question' in x || 'answer' in x) return `${x.question ?? ''}|${x.answer ?? ''}`;
    if ('label' in x || 'value' in x) return `${x.label ?? ''}=${x.value ?? ''}`;
    return Object.entries(x)
      .map(([k, v]) => `${k}=${v}`)
      .join('&');
  }
  return String(x ?? '');
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
  } else if (k === 'rows') {
    parsed = lines.map(line => {
      const idx = line.indexOf('=');
      return idx === -1
        ? { label: line, value: '' }
        : { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() };
    });
  } else {
    parsed = lines;
  }
  block[k] = parsed;
  drafts.value = Object.fromEntries(Object.entries(drafts.value).filter(([draftKey]) => draftKey !== key));
}

function add(): void {
  local.value.push({ type: 'rich_text', title: '' });
}

function remove(i: number): void {
  local.value.splice(i, 1);
  drafts.value = {};
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

        <!-- 富文本 -->
        <template v-if="block.type === 'rich_text'">
          <NFormItem label="正文（支持简单 HTML）" :show-feedback="false">
            <NInput v-model:value="block.html" type="textarea" :rows="4" placeholder="<p>内容段落</p>" />
          </NFormItem>
          <NFormItem label="对齐" :show-feedback="false">
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

        <!-- 规格表 -->
        <template v-else-if="block.type === 'spec_table'">
          <NFormItem :label="hintMap.columns" :show-feedback="false">
            <NInput
              type="textarea"
              :rows="2"
              :value="arrText(i, 'columns')"
              @update:value="(v: string) => setDraft(i, 'columns', v)"
              @blur="commitDraft(i, 'columns')"
            />
          </NFormItem>
          <NFormItem :label="hintMap.spec_table" :show-feedback="false">
            <NInput
              type="textarea"
              :rows="3"
              :value="arrText(i, 'rows')"
              @update:value="(v: string) => setDraft(i, 'rows', v)"
              @blur="commitDraft(i, 'rows')"
            />
          </NFormItem>
        </template>

        <!-- 卖点 -->
        <template v-else-if="block.type === 'features'">
          <NFormItem :label="hintMap.features" :show-feedback="false">
            <NInput
              type="textarea"
              :rows="3"
              :value="arrText(i, 'items')"
              @update:value="(v: string) => setDraft(i, 'items', v)"
              @blur="commitDraft(i, 'items')"
            />
          </NFormItem>
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
  </div>
</template>
