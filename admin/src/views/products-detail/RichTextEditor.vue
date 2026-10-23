<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKitDefault from '@tiptap/starter-kit';
import PlaceholderDefault from '@tiptap/extension-placeholder';
import ImageDefault from '@tiptap/extension-image';
import TextAlignDefault from '@tiptap/extension-text-align';
import { Video as VideoDefault } from './tiptapVideo';
import ResourceInput from '@/components/ResourceInput.vue';
import { marked } from 'marked';
import { NButton, NModal, NSpace, NInput, NTag, NRadioGroup, NRadioButton } from 'naive-ui';

/**
 * 富文本详情块编辑器（TIPTAP + MARKDOWN）。
 * 支持两种模式：
 *  - 富文本：Tiptap 所见即所得（标题/列表/引用/代码块/图片/加粗等）
 *  - Markdown 源码：textarea 编辑，保存时经 marked 渲染为 HTML 落库
 * 保存结果始终为 HTML（与后端 rich_text.html、C 端 v-html 契约一致）。
 */
const props = defineProps<{ show: boolean; html: string; title: string; inline?: boolean }>();
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void;
  (e: 'save', html: string): void;
  (e: 'register', item: { id: string; url: string; [key: string]: any }): void;
}>();

const mode = ref<'rich' | 'md'>('rich');
const mdText = ref('');

// 媒体插入弹层：图片 / 视频统一走 ResourceInput 三入口（上传 / 粘贴 URL / 资源库）
const mediaPop = ref<{ type: 'image' | 'video'; show: boolean }>({ type: 'image', show: false });
const mediaUrl = ref('');
const previewShow = ref(false);
const previewHtml = ref('');

const editor = useEditor({
  content: props.html || '',
  extensions: [
    StarterKitDefault,
    PlaceholderDefault.configure({ placeholder: '输入正文，支持标题、列表、引用、代码块…' }),
    ImageDefault.configure({ inline: false, allowBase64: false }),
    TextAlignDefault.configure({ types: ['heading', 'paragraph'], alignments: ['left', 'center', 'right'] }),
    VideoDefault
  ]
});

// 打开时同步内容；关闭时切换回富文本模式
watch(
  () => props.show,
  v => {
    if (v) {
      mode.value = 'rich';
      editor.value?.commands.setContent(props.html || '', { emitUpdate: false });
    }
  }
);

// 切到 Markdown 源码（内容以纯文本兜底，编辑态在文本域中完成）
function toRich() {
  mode.value = 'rich';
  try {
    const html = marked.parse(mdText.value || '') as string;
    editor.value?.commands.setContent(html, { emitUpdate: false });
  } catch {
    /* 解析失败保留编辑器原内容 */
  }
}

function close() {
  emit('update:show', false);
}

function confirm() {
  const html = mode.value === 'md' ? (marked.parse(mdText.value || '') as string) : editor.value?.getHTML() || '';
  emit('save', html);
  close();
}

const toolbar = computed(() => {
  const e = editor.value;
  if (!e) return [];
  return [
    { key: 'undo', label: '↩', disabled: !e.can().undo(), run: () => e.chain().focus().undo().run() },
    { key: 'redo', label: '↪', disabled: !e.can().redo(), run: () => e.chain().focus().redo().run() },
    { key: 'bold', label: 'B', active: e.isActive('bold'), run: () => e.chain().focus().toggleBold().run() },
    { key: 'italic', label: 'I', active: e.isActive('italic'), run: () => e.chain().focus().toggleItalic().run() },
    { key: 'strike', label: 'S', active: e.isActive('strike'), run: () => e.chain().focus().toggleStrike().run() },
    {
      key: 'h2',
      label: 'H2',
      active: e.isActive('heading', { level: 2 }),
      run: () => e.chain().focus().toggleHeading({ level: 2 }).run()
    },
    {
      key: 'h3',
      label: 'H3',
      active: e.isActive('heading', { level: 3 }),
      run: () => e.chain().focus().toggleHeading({ level: 3 }).run()
    },
    {
      key: 'bullet',
      label: '• 列表',
      active: e.isActive('bulletList'),
      run: () => e.chain().focus().toggleBulletList().run()
    },
    {
      key: 'ordered',
      label: '1. 列表',
      active: e.isActive('orderedList'),
      run: () => e.chain().focus().toggleOrderedList().run()
    },
    {
      key: 'quote',
      label: '❝',
      active: e.isActive('blockquote'),
      run: () => e.chain().focus().toggleBlockquote().run()
    },
    {
      key: 'code',
      label: '</>',
      active: e.isActive('codeBlock'),
      run: () => e.chain().focus().toggleCodeBlock().run()
    },
    { key: 'hr', label: '—', run: () => e.chain().focus().setHorizontalRule().run() },
    {
      key: 'align-left',
      label: '左',
      active: e.isActive({ textAlign: 'left' }),
      run: () => e.chain().focus().setTextAlign('left').run()
    },
    {
      key: 'align-center',
      label: '中',
      active: e.isActive({ textAlign: 'center' }),
      run: () => e.chain().focus().setTextAlign('center').run()
    },
    {
      key: 'align-right',
      label: '右',
      active: e.isActive({ textAlign: 'right' }),
      run: () => e.chain().focus().setTextAlign('right').run()
    }
  ];
});

function openMedia(type: 'image' | 'video') {
  mediaUrl.value = '';
  mediaPop.value = { type, show: true };
}

function applyMedia() {
  const url = mediaUrl.value.trim();
  if (!url || !editor.value) return;
  if (mediaPop.value.type === 'image') {
    editor.value.chain().focus().setImage({ src: url }).run();
  } else {
    editor.value.chain().focus().setVideo({ src: url }).run();
  }
  mediaPop.value.show = false;
  mediaUrl.value = '';
}

/** 预览按钮：md 模式切回富文本渲染；rich 模式打开只读 HTML 预览视图 */
function openPreview() {
  if (mode.value === 'md') {
    toRich();
    return;
  }
  previewHtml.value = editor.value?.getHTML() || '';
  previewShow.value = true;
}
</script>

<template>
  <NModal
    v-if="!props.inline"
    :show="props.show"
    preset="card"
    :title="`富文本编辑：${props.title || '正文'}`"
    style="width: 860px"
    @update:show="(v: boolean) => (v ? undefined : close())"
  >
    <div class="flex items-center justify-between mb-3">
      <NRadioGroup v-model:value="mode">
        <NRadioButton value="rich">富文本</NRadioButton>
        <NRadioButton value="md">Markdown 源码</NRadioButton>
      </NRadioGroup>
      <NTag v-if="mode === 'md'" size="small" type="info">保存时自动渲染为 HTML</NTag>
    </div>

    <template v-if="mode === 'rich' && editor">
      <div class="flex flex-wrap items-center gap-1 border border-gray-200 rounded-t-md bg-gray-50 p-1.5">
        <button
          v-for="btn in toolbar"
          :key="btn.key"
          type="button"
          class="min-w-7 h-7 px-1.5 rounded text-xs"
          :class="btn.active ? 'bg-primary-100 text-primary-600 font-semibold' : 'hover:bg-gray-200'"
          :disabled="btn.disabled"
          @click="btn.run"
        >
          {{ btn.label }}
        </button>
        <button
          type="button"
          class="min-w-7 h-7 px-1.5 rounded text-xs hover:bg-gray-200"
          title="插入图片"
          @click="openMedia('image')"
        >
          🖼
        </button>
        <button
          type="button"
          class="min-w-7 h-7 px-1.5 rounded text-xs hover:bg-gray-200"
          title="插入视频"
          @click="openMedia('video')"
        >
          🎬
        </button>
      </div>
      <div
        class="border border-t-0 border-gray-200 rounded-b-md bg-white p-3 min-h-[240px] max-h-[50vh] overflow-auto prose prose-sm max-w-none"
      >
        <EditorContent :editor="editor" />
      </div>
    </template>

    <template v-else>
      <NInput
        v-model:value="mdText"
        type="textarea"
        :rows="14"
        placeholder="# 标题&#10;&#10;正文段落，支持 **加粗**、- 列表、1. 列表、> 引用、`代码`"
      />
      <p class="text-xs opacity-60 mt-1">支持 GFM 语法：标题、加粗、列表、引用、代码块、表格等</p>
    </template>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="close">取消</NButton>
        <NButton @click="openPreview">{{ mode === 'md' ? '预览（切回富文本）' : '预览' }}</NButton>
        <NButton type="primary" @click="confirm">保存</NButton>
      </NSpace>
    </template>
  </NModal>

  <!-- 内联模式：卡片内展开编辑器 -->
  <div v-else-if="props.show" class="flex flex-col gap-2 rounded-md border border-gray-200 bg-gray-50 p-3">
    <div class="flex items-center justify-between">
      <NRadioGroup v-model:value="mode" size="small">
        <NRadioButton value="rich">富文本</NRadioButton>
        <NRadioButton value="md">Markdown 源码</NRadioButton>
      </NRadioGroup>
      <NTag v-if="mode === 'md'" size="small" type="info">保存时自动渲染为 HTML</NTag>
    </div>

    <template v-if="mode === 'rich' && editor">
      <div class="flex flex-wrap items-center gap-1 border border-gray-200 rounded-t-md bg-gray-50 p-1.5">
        <button
          v-for="btn in toolbar"
          :key="btn.key"
          type="button"
          class="min-w-7 h-7 px-1.5 rounded text-xs"
          :class="btn.active ? 'bg-primary-100 text-primary-600 font-semibold' : 'hover:bg-gray-200'"
          :disabled="btn.disabled"
          @click="btn.run"
        >
          {{ btn.label }}
        </button>
        <button
          type="button"
          class="min-w-7 h-7 px-1.5 rounded text-xs hover:bg-gray-200"
          title="插入图片"
          @click="openMedia('image')"
        >
          🖼
        </button>
        <button
          type="button"
          class="min-w-7 h-7 px-1.5 rounded text-xs hover:bg-gray-200"
          title="插入视频"
          @click="openMedia('video')"
        >
          🎬
        </button>
      </div>
      <div
        class="border border-t-0 border-gray-200 rounded-b-md bg-white p-3 min-h-[200px] max-h-[45vh] overflow-auto prose prose-sm max-w-none rich-content"
      >
        <EditorContent :editor="editor" />
      </div>
    </template>

    <template v-else>
      <NInput
        v-model:value="mdText"
        type="textarea"
        :rows="8"
        placeholder="# 标题&#10;&#10;正文段落，支持 **加粗**、- 列表、1. 列表、> 引用、`代码`"
      />
      <p class="text-xs opacity-60">支持 GFM 语法：标题、加粗、列表、引用、代码块、表格等</p>
    </template>

    <div class="flex justify-end gap-2">
      <NButton size="small" @click="close">取消</NButton>
      <NButton size="small" @click="openPreview">{{ mode === 'md' ? '预览（切回富文本）' : '预览' }}</NButton>
      <NButton size="small" type="primary" @click="confirm">保存</NButton>
    </div>
  </div>

  <!-- 媒体插入弹层（三入口） -->
  <NModal
    v-model:show="mediaPop.show"
    preset="card"
    :title="`插入${mediaPop.type === 'image' ? '图片' : '视频'}`"
    style="width: 640px"
  >
    <ResourceInput v-model="mediaUrl" :type="mediaPop.type" @register="(it: any) => emit('register', it)" />
    <template #footer>
      <NSpace justify="end">
        <NButton size="small" @click="mediaPop.show = false">取消</NButton>
        <NButton size="small" type="primary" :disabled="!mediaUrl.trim()" @click="applyMedia">插入</NButton>
      </NSpace>
    </template>
  </NModal>

  <!-- 只读预览视图（rich 模式） -->
  <NModal v-model:show="previewShow" preset="card" title="预览" style="width: 760px">
    <div class="max-h-[60vh] overflow-auto prose prose-sm max-w-none rich-content" v-html="previewHtml" />
  </NModal>
</template>

<style scoped>
/* 富文本编辑/预览内容媒体约束：图片/视频铺满内容区（小图放大、大图限宽 1080）保持比例居中 */
.rich-content :deep(img),
.rich-content :deep(video) {
  width: 100% !important;
  max-width: min(100%, 1080px);
  height: auto !important;
  display: block;
  margin: 0.75rem auto;
  border-radius: 0.5rem;
}
</style>
