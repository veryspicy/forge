<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import { useRouter } from 'vue-router';
import { resourceApi } from '@/service/api/resources';
import { marked } from 'marked';
import { renderAsync } from 'docx-preview';
import JSZip from 'jszip';

interface ResourceItem {
  id: string;
  url: string;
  thumb_url?: string;
  file_type: string;
  mime: string;
  file_size: number;
  name: string;
  created_at: string;
  object_key: string;
  directory?: string;
  tags?: string[];
  ref_count?: number;
  deleted_at?: string | null;
}

interface RefInfo {
  ref_type: string;
  ref_id: string;
  ref_label: string;
}

const dialog = useDialog();
const message = useMessage();
const router = useRouter();

const typeTabs = [
  { key: '', label: '全部', icon: 'mdi:view-grid-outline' },
  { key: 'image', label: '图片', icon: 'mdi:image-outline' },
  { key: 'video', label: '视频', icon: 'mdi:video-outline' },
  { key: 'audio', label: '音频', icon: 'mdi:music-note-outline' },
  { key: 'document', label: '文档', icon: 'mdi:file-document-outline' }
];

const activeType = ref('');
const keyword = ref('');
const activeDirectory = ref<string | null>(null); // null=不过滤，''=未归档
const activeTag = ref('');
const directories = ref<{ directory: string; count: number }[]>([]);
const tags = ref<{ name: string; count: number }[]>([]);
const items = ref<ResourceItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(30);
const loading = ref(false);
const uploading = ref(false);
const selectedIds = ref<Set<string>>(new Set());
const currentDetail = ref<ResourceItem | null>(null);
const currentRefs = ref<RefInfo[]>([]);
const renameValue = ref('');
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
const dragActive = ref(false);
const dragResourceIds = ref<string[]>([]);
const tagInputValue = ref('');
const trashVisible = ref(false);
const trashItems = ref<ResourceItem[]>([]);
const trashTotal = ref(0);
const trashPage = ref(1);
const trashPageSize = ref(24);
const trashLoading = ref(false);
const trashKeyword = ref('');
const trashSelected = ref<Set<string>>(new Set());
const moveDialogVisible = ref(false);
const moveTargetDir = ref('');
const tagDialogVisible = ref(false);
const uploadQueue = ref(0);
const uploadTotal = ref(0);
const uploadDone = ref(0);
const previewVisible = ref(false);
const previewUrl = ref('');
type PreviewType = 'image' | 'video' | 'audio' | 'pdf' | 'docx' | 'md' | 'text' | 'zip' | 'other';
const previewType = ref<PreviewType>('other');
const previewText = ref('');
const previewHtml = ref('');
const previewDocxRef = ref<HTMLElement | null>(null);
const zipFiles = ref<string[]>([]);
const zipLoading = ref(false);
const gridScrollRef = ref<HTMLElement | null>(null);
let smoothScrollCleanup: (() => void) | null = null;

/** 为网格容器绑定平滑滚动：限制单次滚轮增量 + rAF 缓动，降低顿挫感 */
function bindSmoothScroll(el: HTMLElement | null) {
  smoothScrollCleanup?.();
  if (!el) return;
  const scrollEl = el;
  let current = scrollEl.scrollTop;
  let target = scrollEl.scrollTop;
  let rafId: number | null = null;

  function onWheel(e: WheelEvent) {
    e.preventDefault();
    const maxStep = 80; // 单次滚轮最大滚动距离（px），控制滑动速度
    const delta = Math.max(-maxStep, Math.min(maxStep, e.deltaY));
    const maxScroll = scrollEl.scrollHeight - scrollEl.clientHeight;
    target = Math.max(0, Math.min(target + delta, maxScroll));
    if (rafId !== null) return;
    current = scrollEl.scrollTop;
    const tick = () => {
      const diff = target - current;
      if (Math.abs(diff) < 0.5) {
        scrollEl.scrollTop = target;
        rafId = null;
        return;
      }
      current += diff * 0.18; // 缓动系数：越小越平滑
      scrollEl.scrollTop = current;
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
  }

  scrollEl.addEventListener('wheel', onWheel, { passive: false });
  smoothScrollCleanup = () => {
    scrollEl.removeEventListener('wheel', onWheel);
    if (rafId !== null) cancelAnimationFrame(rafId);
  };
}

const typeCounts = computed(() => {
  const map: Record<string, number> = {};
  for (const t of typeTabs) {
    if (!t.key) continue;
    map[t.key] = items.value.filter(i => i.file_type === t.key).length;
  }
  return map;
});

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

const TEXT_EXTENSIONS = [
  'txt',
  'json',
  'csv',
  'xml',
  'yml',
  'yaml',
  'log',
  'ini',
  'conf',
  'sql',
  'sh',
  'py',
  'js',
  'ts',
  'html',
  'css',
  'env',
  'gitignore'
];

function resolvePreviewType(r: ResourceItem): PreviewType {
  if (isPreviewableImage(r)) return 'image';
  if (isPreviewableVideo(r)) return 'video';
  if (isPreviewableAudio(r)) return 'audio';
  const ext = (r.name.split('.').pop() || '').toLowerCase();
  if (ext === 'pdf') return 'pdf';
  if (ext === 'docx') return 'docx';
  if (ext === 'zip') return 'zip';
  if (ext === 'md') return 'md';
  if (TEXT_EXTENSIONS.includes(ext)) return 'text';
  return 'other';
}

function openPreview(r: ResourceItem) {
  previewUrl.value = r.url;
  previewType.value = resolvePreviewType(r);
  previewVisible.value = true;
}

/** 文本/md/docx/zip 类资源：打开弹窗后异步加载内容 */
async function loadPreviewContent() {
  previewText.value = '';
  previewHtml.value = '';
  zipFiles.value = [];
  zipLoading.value = false;
  if (!previewUrl.value) return;

  if (previewType.value === 'text' || previewType.value === 'md') {
    try {
      const res = await fetch(previewUrl.value);
      const text = await res.text();
      previewText.value = text;
      if (previewType.value === 'md') {
        previewHtml.value = marked.parse(text) as string;
      }
    } catch {
      previewText.value = '预览内容加载失败，可通过下载查看';
    }
    return;
  }

  if (previewType.value === 'docx') {
    try {
      const res = await fetch(previewUrl.value);
      const blob = await res.blob();
      if (previewDocxRef.value) {
        previewDocxRef.value.innerHTML = '';
        await renderAsync(blob, previewDocxRef.value, undefined, {
          ignoreLastRenderedPageBreak: true,
          useBase64URL: true
        });
      }
    } catch {
      if (previewDocxRef.value) {
        previewDocxRef.value.innerHTML =
          '<p class="p-4 text-center text-sm text-gray-400">docx 渲染失败，可通过下载查看</p>';
      }
    }
    return;
  }

  if (previewType.value === 'zip') {
    zipLoading.value = true;
    try {
      const res = await fetch(previewUrl.value);
      const blob = await res.blob();
      const zip = await JSZip.loadAsync(blob);
      zipFiles.value = Object.keys(zip.files).filter(name => !zip.files[name].dir);
    } catch {
      zipFiles.value = ['压缩包解析失败，可通过下载查看'];
    } finally {
      zipLoading.value = false;
    }
  }
}

watch(
  previewVisible,
  visible => {
    if (visible) {
      loadPreviewContent();
    }
  },
  { flush: 'post' }
);

async function loadList() {
  loading.value = true;
  try {
    const res = await resourceApi.list({
      type: activeType.value || undefined,
      keyword: keyword.value || undefined,
      directory: activeDirectory.value !== null ? activeDirectory.value : undefined,
      tag: activeTag.value || undefined,
      page: page.value,
      page_size: pageSize.value
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

async function loadMeta() {
  try {
    const [dirRes, tagRes] = await Promise.all([resourceApi.directories(), resourceApi.tags()]);
    const dirData = (dirRes as any).data?.data ?? (dirRes as any).data ?? [];
    const tagData = (tagRes as any).data?.data ?? (tagRes as any).data ?? [];
    directories.value = Array.isArray(dirData) ? dirData : [];
    tags.value = Array.isArray(tagData) ? tagData : [];
  } catch {
    // 元数据加载失败不阻塞主列表
  }
}

function selectType(key: string) {
  activeType.value = key;
  page.value = 1;
  loadList();
}

// ---------------------------------------------------------------------------
// 回收站
// ---------------------------------------------------------------------------
async function loadTrash() {
  trashLoading.value = true;
  try {
    const res = (await resourceApi.trashList({
      keyword: trashKeyword.value || undefined,
      page: trashPage.value,
      page_size: trashPageSize.value
    })) as any;
    const data = res?.data?.data ?? res?.data ?? res;
    trashItems.value = data?.items ?? [];
    trashTotal.value = data?.total ?? 0;
  } catch (e: any) {
    message.error(`加载回收站失败: ${e?.message || e}`);
  } finally {
    trashLoading.value = false;
  }
}

function openTrash() {
  trashVisible.value = true;
  trashPage.value = 1;
  trashSelected.value = new Set();
  loadTrash();
}

function onTrashSearch() {
  trashPage.value = 1;
  loadTrash();
}

function onTrashPageChange(p: number) {
  trashPage.value = p;
  loadTrash();
}

function toggleTrashSelect(id: string) {
  const s = new Set(trashSelected.value);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  trashSelected.value = s;
}

async function restoreTrashSelection() {
  if (!trashSelected.value.size) {
    message.warning('请先勾选要恢复的资源');
    return;
  }
  const ids = Array.from(trashSelected.value);
  dialog.warning({
    title: '确认恢复',
    content: `确定恢复选中的 ${ids.length} 个资源吗？恢复后重新出现在资源列表。`,
    positiveText: '恢复',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = (await resourceApi.restoreTrash(ids)) as any;
        const data = res?.data?.data ?? res?.data ?? res;
        message.success(`已恢复 ${data?.restored ?? ids.length} 个资源`);
        trashSelected.value = new Set();
        loadTrash();
        loadList();
      } catch (e: any) {
        message.error(`恢复失败: ${e?.message || e}`);
      }
    }
  });
}

async function purgeTrashSelection() {
  if (!trashSelected.value.size) {
    message.warning('请先勾选要彻底删除的资源');
    return;
  }
  const ids = Array.from(trashSelected.value);
  dialog.warning({
    title: '确认彻底删除',
    content: `将永久删除选中的 ${ids.length} 个资源（MinIO 文件与数据库记录一并清除，不可恢复）。确定继续？`,
    positiveText: '彻底删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = (await resourceApi.purgeTrash(ids)) as any;
        const data = res?.data?.data ?? res?.data ?? res;
        message.success(`已彻底删除 ${data?.purged ?? ids.length} 个资源`);
        trashSelected.value = new Set();
        loadTrash();
        loadMeta();
      } catch (e: any) {
        message.error(`彻底删除失败: ${e?.message || e}`);
      }
    }
  });
}

async function emptyTrashAll() {
  if (!trashTotal.value) return;
  dialog.warning({
    title: '清空回收站',
    content: `将永久删除回收站全部 ${trashTotal.value} 个资源，不可恢复。确定继续？`,
    positiveText: '清空',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = (await resourceApi.emptyTrash()) as any;
        const data = res?.data?.data ?? res?.data ?? res;
        message.success(`已清空回收站（${data?.purged ?? trashTotal.value} 个）`);
        trashSelected.value = new Set();
        loadTrash();
        loadMeta();
      } catch (e: any) {
        message.error(`清空失败: ${e?.message || e}`);
      }
    }
  });
}

function selectDirectory(dir: string) {
  activeDirectory.value = activeDirectory.value === dir ? null : dir;
  activeTag.value = '';
  page.value = 1;
  loadList();
}

function selectTag(tag: string) {
  activeTag.value = activeTag.value === tag ? '' : tag;
  activeDirectory.value = null;
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

async function triggerUpload() {
  const w = window as any;
  if (w.showOpenFilePicker) {
    try {
      const handles = await w.showOpenFilePicker({ multiple: true });
      const files = await Promise.all(handles.map((h: any) => h.getFile()));
      uploadFiles(files.map(f => ({ file: f })));
      return;
    } catch (err: any) {
      if (err?.name === 'AbortError') return; // 用户取消选择
    }
  }
  fileInput.value?.click();
}

/** 递归读取目录句柄，保留相对目录结构（File System Access API） */
async function collectDirHandle(dirHandle: any): Promise<{ file: File; directory?: string }[]> {
  const out: { file: File; directory?: string }[] = [];
  async function walk(handle: any, prefix: string) {
    for await (const entry of handle.values()) {
      if (entry.kind === 'file') {
        out.push({ file: await entry.getFile(), directory: prefix || undefined });
      } else if (entry.kind === 'directory') {
        await walk(entry, prefix ? `${prefix}/${entry.name}` : entry.name);
      }
    }
  }
  await walk(dirHandle, '');
  return out;
}

async function triggerFolderUpload() {
  const w = window as any;
  if (w.showDirectoryPicker) {
    try {
      const dirHandle = await w.showDirectoryPicker({ mode: 'read' });
      const list = await collectDirHandle(dirHandle);
      if (!list.length) return;
      uploadFiles(list);
      return;
    } catch (err: any) {
      if (err?.name === 'AbortError') return; // 用户取消选择
    }
  }
  folderInput.value?.click();
}

const folderOption = [
  {
    label: '上传文件夹',
    key: 'folder',
    props: {
      class: 'upload-folder-option'
    }
  }
];

function onFolderSelect() {
  triggerFolderUpload();
}

/** 解析拖拽的文件列表，支持文件与文件夹混拖 */
function collectDropFiles(dataTransfer: DataTransfer): Promise<{ file: File; directory?: string }[]> {
  const entries = Array.from(dataTransfer.items || [])
    .map(item => item.webkitGetAsEntry?.() as any)
    .filter(Boolean);
  const results: { file: File; directory?: string }[] = [];

  async function walk(entry: any, dirPath = ''): Promise<void> {
    if (entry.isFile) {
      const file = await new Promise<File>((resolve, reject) => {
        entry.file(resolve, reject);
      });
      results.push({ file, directory: dirPath || undefined });
      return;
    }
    if (entry.isDirectory) {
      const reader = entry.createReader();
      const children: any[] = [];
      // 一次性读可能截断，循环读直到为空
      for (;;) {
        const batch = await new Promise<any[]>((resolve, reject) => {
          reader.readEntries(resolve, reject);
        });
        if (!batch.length) break;
        children.push(...batch);
      }
      const subPath = dirPath ? `${dirPath}/${entry.name}` : entry.name;
      for (const child of children) {
        await walk(child, subPath);
      }
    }
  }

  return (async () => {
    for (const entry of entries) {
      await walk(entry);
    }
    return results;
  })();
}

/** 上传前批量重名检测：返回已占用名称集合（用于自动加后缀） */
async function fetchExistingNames(names: string[]): Promise<Set<string>> {
  try {
    const res = (await resourceApi.checkNames(names)) as any;
    const info = res?.data?.data ?? res?.data ?? res;
    const existing = info?.existing ?? {};
    return new Set(Object.keys(existing));
  } catch {
    return new Set();
  }
}

/** 将同名文件自动重命名为 name(1).ext / name(2).ext，返回新 File 列表。
 * 迭代检查：每轮把当前候选名提交服务器核对，冲突项继续递增，直到全部无冲突。
 * 修复连续上传同名文件时重复生成相同 (n) 后缀的问题（如第二次仍生成 (1) 而非 (2)）。 */
async function dedupeUploadList(list: { file: File; directory?: string }[]) {
  const pending = list.map(item => {
    const { file } = item;
    const dot = file.name.lastIndexOf('.');
    return {
      item,
      stem: dot > 0 ? file.name.slice(0, dot) : file.name,
      ext: dot > 0 ? file.name.slice(dot) : '',
      candidate: file.name
    };
  });

  // 迭代直至稳定：候选名被服务器占用或批内占用时递增 (n)，新候选名再交给服务器核对
  for (;;) {
    const names = pending.map(p => p.candidate);
    const existing = await fetchExistingNames(names);
    const used = new Set(existing); // 服务器已占用 + 本批已分配
    let dirty = false;
    for (const p of pending) {
      let seq = 0;
      while (used.has(p.candidate)) {
        dirty = true;
        seq += 1;
        p.candidate = `${p.stem}(${seq})${p.ext}`;
        if (!used.has(p.candidate)) break;
      }
      used.add(p.candidate);
    }
    if (!dirty) break;
  }

  return pending.map(p => {
    if (p.candidate === p.item.file.name) return p.item;
    return {
      directory: p.item.directory,
      file: new File([p.item.file], p.candidate, { type: p.item.file.type })
    };
  });
}

/** 顺序上传文件队列：每个成功后短暂停留，全部完成汇总提示 */
async function uploadFiles(list: { file: File; directory?: string }[]) {
  if (!list.length) return;
  const finalList = await dedupeUploadList(list);
  if (finalList.some((item, idx) => item.file.name !== list[idx].file.name)) {
    message.info('检测到同名文件，已自动重命名（如 name(1).png）后上传');
  }
  uploadTotal.value = finalList.length;
  uploadDone.value = 0;
  uploading.value = true;
  let okCount = 0;
  let failCount = 0;
  for (const item of finalList) {
    uploadQueue.value += 1;
    try {
      const res = await resourceApi.upload(item.file, {
        directory: item.directory,
        tags: item.directory ? [item.directory] : undefined
      });
      const data = (res as any).data?.data ?? (res as any).data;
      okCount += 1;
      message.success(`「${item.file.name}」上传成功`);
      if (data?.id && finalList.length === 1) selectDetail(data);
      await new Promise(resolve => setTimeout(resolve, 300));
    } catch {
      failCount += 1;
      // 请求层已弹出错误消息，这里仅计数，避免双弹窗
    } finally {
      uploadQueue.value -= 1;
      uploadDone.value += 1;
    }
  }
  uploading.value = false;
  await Promise.all([loadList(), loadMeta()]);
  if (failCount === 0) {
    message.success(`全部 ${okCount} 个文件上传完成`);
  } else if (okCount > 0) {
    message.warning(`上传完成：成功 ${okCount} 个，失败 ${failCount} 个`);
  } else {
    message.error(`全部 ${failCount} 个文件上传失败`);
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = '';
  if (!files.length) return;
  uploadFiles(files.map(f => ({ file: f })));
}

function onFolderChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = '';
  if (!files.length) return;
  // 文件夹选择器会带 webkitRelativePath，如 folder/sub/file.png
  const list = files.map(f => {
    const rel = f.webkitRelativePath || '';
    const seg = rel.split('/');
    const directory = seg.length > 1 ? seg[0] : undefined;
    return { file: f, directory };
  });
  uploadFiles(list);
}

function onDrop(e: DragEvent) {
  dragActive.value = false;
  if (!e.dataTransfer) return;
  collectDropFiles(e.dataTransfer).then(uploadFiles);
}

function toggleSelect(id: string) {
  const s = new Set(selectedIds.value);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  selectedIds.value = s;
  // 多选态下右侧面板显示"N 项已选中"；清空时若存在当前详情则保持
  if (selectedIds.value.size > 1) {
    currentDetail.value = null;
  }
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
  } catch {
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
  if (name !== currentDetail.value.name) {
    try {
      const check = (await resourceApi.checkName(name, currentDetail.value.id)) as any;
      const info = check?.data?.data ?? check?.data ?? check;
      if (info?.exists) {
        message.warning(
          `重名提示：已有 ${info.active_count} 个同名资源${info.trash_count ? `（回收站 ${info.trash_count} 个）` : ''}，请更换名称`
        );
        return;
      }
    } catch {
      // 检测失败不阻塞重命名
    }
  }
  try {
    await resourceApi.rename(currentDetail.value.id, name);
    message.success('重命名成功');
    currentDetail.value.name = name;
    await Promise.all([loadList(), loadMeta()]);
  } catch (e: any) {
    message.error(`重命名失败: ${e?.message || e}`);
  }
}

/** 卡片拖拽开始：记录拖拽的资源 id（多选时拖全部选中项） */
function onCardDragStart(e: DragEvent, r: ResourceItem) {
  dragResourceIds.value = selectedIds.value.has(r.id) ? Array.from(selectedIds.value) : [r.id];
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragResourceIds.value.join(','));
  }
}

/** 目录树条目接收拖拽：移动到该目录 */
async function onDirDrop(dir: string) {
  const ids = dragResourceIds.value;
  dragResourceIds.value = [];
  if (!ids.length) return;
  try {
    const res = (await resourceApi.move(ids, dir)) as any;
    const data = res?.data?.data ?? res?.data ?? res;
    const moved = data?.moved ?? ids.length;
    message.success(`已移动 ${moved} 个资源到「${dir || '未归档'}」`);
    await Promise.all([loadList(), loadMeta()]);
  } catch (e: any) {
    message.error(`移动失败: ${e?.message || e}`);
  }
}

/** 批量移动到目录：弹窗选择 */
function showMoveDialog() {
  const ids = Array.from(selectedIds.value);
  if (!ids.length) {
    message.warning('请先选择资源');
    return;
  }
  moveTargetDir.value = '';
  moveDialogVisible.value = true;
}

async function confirmMove() {
  const ids = Array.from(selectedIds.value);
  try {
    const res = (await resourceApi.move(ids, moveTargetDir.value)) as any;
    const data = res?.data?.data ?? res?.data ?? res;
    const moved = data?.moved ?? ids.length;
    message.success(`已移动 ${moved} 个资源到「${moveTargetDir.value || '未归档'}」`);
    moveDialogVisible.value = false;
    await Promise.all([loadList(), loadMeta()]);
  } catch (e: any) {
    message.error(`移动失败: ${e?.message || e}`);
  }
}

/** 批量打标：弹窗输入标签（逗号/空格分隔） */
function showTagDialog() {
  const ids = Array.from(selectedIds.value);
  if (!ids.length) {
    message.warning('请先选择资源');
    return;
  }
  tagInputValue.value = '';
  tagDialogVisible.value = true;
}

async function confirmTags() {
  const ids = Array.from(selectedIds.value);
  const tagList = tagInputValue.value
    .split(/[,，\s]+/)
    .map(t => t.trim())
    .filter(Boolean);
  if (!tagList.length) {
    message.warning('请输入标签');
    return;
  }
  try {
    (await resourceApi.setTags(ids, tagList)) as any;
    message.success(`已为 ${ids.length} 个资源添加 ${tagList.length} 个标签`);
    tagDialogVisible.value = false;
    await Promise.all([loadList(), loadMeta()]);
  } catch (e: any) {
    message.error(`打标失败: ${e?.message || e}`);
  }
}

/** 引用跳转：ref_type 映射到对应管理路由 */
const REF_ROUTE_MAP: Record<string, string> = {
  product: '/products',
  products: '/products',
  article: '/ai-probe',
  articles: '/ai-probe',
  order: '/orders',
  orders: '/orders',
  user: '/users',
  users: '/users',
  supplier: '/suppliers',
  suppliers: '/suppliers',
  shipment: '/shipments',
  shipments: '/shipments',
  site: '/site-config'
};

function canJumpRef(refInfo: RefInfo) {
  return Boolean(REF_ROUTE_MAP[refInfo.ref_type]);
}

function jumpToRef(refInfo: RefInfo) {
  const target = REF_ROUTE_MAP[refInfo.ref_type];
  if (!target) {
    message.info(`引用位置「${refInfo.ref_label}」暂无跳转路由（ref_type=${refInfo.ref_type}）`);
    return;
  }
  // product 类引用直接跳到对应商品详情页，并携带当前资源 id 用于高亮定位引用图片
  if (refInfo.ref_type === 'product' || refInfo.ref_type === 'products') {
    router.push({
      path: `/products/${refInfo.ref_id}`,
      query: currentDetail.value?.id ? { highlight_resource: String(currentDetail.value.id) } : {}
    });
    return;
  }
  router.push(target);
}

async function doDelete(r: ResourceItem) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除资源「${r.name}」吗？（软删，不影响已引用位置）`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      // 请求层 onError 已全局弹出错误消息，这里只处理成功分支，避免双弹窗
      const { data } = (await resourceApi.remove(r.id)) as any;
      if (!data) return;
      message.success('已删除');
      selectedIds.value.delete(r.id);
      selectedIds.value = new Set(selectedIds.value);
      if (currentDetail.value?.id === r.id) currentDetail.value = null;
      await Promise.all([loadList(), loadMeta()]);
    }
  });
}

async function doBatchDelete() {
  const ids = Array.from(selectedIds.value);
  if (!ids.length) {
    message.warning('请先选择资源');
    return;
  }
  // 拦截：选中的资源中包含被引用资源，取消删除并提示
  const refItem = items.value.find(it => ids.includes(it.id) && (it.ref_count ?? 0) > 0);
  if (refItem) {
    message.warning('选中的资源中包含被引用的资源，请将其释放后再试');
    return;
  }
  dialog.warning({
    title: '确认批量删除',
    content: `确定删除选中的 ${ids.length} 个资源吗？（软删）`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { data } = (await resourceApi.batchRemove(ids)) as any;
      if (!data) return;
      const deletedCount = data?.data?.deleted ?? data?.deleted ?? ids.length;
      message.success(`已删除 ${deletedCount} 个`);
      selectedIds.value = new Set();
      currentDetail.value = null;
      await Promise.all([loadList(), loadMeta()]);
    }
  });
}

async function handleCleanupInvalidRefs() {
  const { data } = (await resourceApi.cleanupInvalidRefs({ dryRun: true })) as any;
  const result = data?.data ?? {};
  const invalid: Array<{ ref_type: string; ref_id: string; ref_label: string; reason: string }> = result.invalid ?? [];
  if (!invalid.length) {
    message.success('未发现无效引用');
    return;
  }
  dialog.warning({
    title: '清理无效引用',
    content: `共发现 ${invalid.length} 条无效引用，清理后对应资源将解除占用、可正常删除。确认继续？`,
    positiveText: '清理',
    negativeText: '取消',
    onPositiveClick: async () => {
      const resp = (await resourceApi.cleanupInvalidRefs({ dryRun: false })) as any;
      const cleaned = resp?.data?.data?.cleaned ?? 0;
      message.success(`已清理 ${cleaned} 条无效引用`);
      currentDetail.value = null;
      await Promise.all([loadList(), loadMeta()]);
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

onMounted(() => {
  loadList();
  loadMeta();
  bindSmoothScroll(gridScrollRef.value);
});

onBeforeUnmount(() => {
  smoothScrollCleanup?.();
});
</script>

<template>
  <div class="resource-page flex gap-4" style="min-height: calc(100vh - 180px)">
    <!-- 左：资源类型 / 目录 / 标签 -->
    <div class="flex w-[220px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <div class="flex items-center gap-2 border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700">
        <SvgIcon icon="mdi:folder-multiple-image" class="text-18px text-green-600" />
        <span class="text-sm font-semibold">资源管理</span>
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        <div class="mb-1 text-xs text-gray-400">类型</div>
        <div class="mb-2 flex flex-col gap-1">
          <div
            v-for="t in typeTabs"
            :key="t.key"
            class="flex cursor-pointer items-center justify-between rounded px-2 py-1.5 text-sm transition-colors"
            :class="
              activeType === t.key
                ? 'bg-green-50 text-green-700 font-medium dark:bg-green-900/20 dark:text-green-400'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800'
            "
            @click="selectType(t.key)"
          >
            <span class="flex items-center gap-2">
              <SvgIcon :icon="t.icon" class="text-16px shrink-0" />
              {{ t.label }}
            </span>
            <span
              v-if="t.key && typeCounts[t.key]"
              class="rounded-full bg-gray-100 px-1.5 text-xs text-gray-500 dark:bg-gray-800"
            >
              {{ typeCounts[t.key] }}
            </span>
          </div>
        </div>

        <div class="mb-1 mt-3 flex items-center justify-between text-xs text-gray-400">
          <span class="flex items-center gap-1">
            <SvgIcon icon="mdi:folder-outline" class="text-13px" />
            目录
          </span>
          <span
            v-if="activeDirectory !== null"
            class="cursor-pointer text-green-500"
            @click="selectDirectory(activeDirectory as string)"
          >
            清除
          </span>
        </div>
        <div class="mb-2 flex flex-col gap-0.5">
          <div
            v-for="d in directories"
            :key="d.directory"
            class="flex cursor-grab items-center justify-between rounded px-2 py-1.5 text-sm transition-colors"
            :class="
              activeDirectory === d.directory
                ? 'bg-green-50 text-green-700 font-medium dark:bg-green-900/20 dark:text-green-400'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800'
            "
            @click="selectDirectory(d.directory)"
            @dragover.prevent
            @drop.prevent="onDirDrop(d.directory)"
          >
            <span class="flex items-center gap-1.5 truncate" :title="d.directory || '未归档'">
              <SvgIcon
                :icon="d.directory ? 'mdi:folder-outline' : 'mdi:folder-open-outline'"
                class="text-15px shrink-0 text-gray-400"
              />
              <span class="truncate">{{ d.directory || '未归档' }}</span>
            </span>
            <span class="rounded-full bg-gray-100 px-1.5 text-xs text-gray-500 dark:bg-gray-800">{{ d.count }}</span>
          </div>
          <div v-if="!directories.length" class="px-2 py-1 text-xs text-gray-400">暂无目录</div>
        </div>

        <div class="mb-1 mt-3 flex items-center justify-between text-xs text-gray-400">
          <span class="flex items-center gap-1">
            <SvgIcon icon="mdi:tag-multiple-outline" class="text-13px" />
            标签
          </span>
          <span v-if="activeTag" class="cursor-pointer text-green-500" @click="selectTag(activeTag)">清除</span>
        </div>
        <div class="flex flex-col gap-0.5">
          <div
            v-for="t in tags"
            :key="t.name"
            class="flex cursor-pointer items-center justify-between rounded px-2 py-1.5 text-sm transition-colors"
            :class="
              activeTag === t.name
                ? 'bg-green-50 text-green-700 font-medium dark:bg-green-900/20 dark:text-green-400'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800'
            "
            @click="selectTag(t.name)"
          >
            <span class="flex items-center gap-1.5 truncate" :title="t.name">
              <SvgIcon icon="mdi:tag-outline" class="text-15px shrink-0 text-gray-400" />
              <span class="truncate">{{ t.name }}</span>
            </span>
            <span class="rounded-full bg-gray-100 px-1.5 text-xs text-gray-500 dark:bg-gray-800">{{ t.count }}</span>
          </div>
          <div v-if="!tags.length" class="px-2 py-1 text-xs text-gray-400">暂无标签</div>
        </div>
      </div>
      <div class="border-t border-gray-100 border-solid p-2 dark:border-gray-700">
        <NButton size="small" secondary block @click="openTrash">
          <template #icon><SvgIcon icon="mdi:delete-restore-outline" class="text-16px" /></template>
          回收站
        </NButton>
      </div>
    </div>

    <!-- 中：资源列表 -->
    <div class="flex flex-1 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <!-- 工具栏 -->
      <div
        class="flex items-center justify-between gap-2 border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700"
      >
        <div class="flex items-center gap-2">
          <div class="flex items-center">
            <NDropdown
              trigger="click"
              :options="folderOption"
              placement="bottom-start"
              :dropdown-props="{ class: 'upload-folder-menu' }"
              @select="onFolderSelect"
            >
              <div class="flex items-center">
                <NButton
                  type="primary"
                  size="small"
                  :loading="uploading"
                  class="!rounded-r-none"
                  @click.stop="triggerUpload"
                >
                  <template #icon><SvgIcon icon="mdi:upload" class="text-16px" /></template>
                  上传
                </NButton>
                <NButton type="primary" size="small" :loading="uploading" class="!rounded-l-none">
                  <template #icon><SvgIcon icon="mdi:chevron-down" class="text-16px" /></template>
                </NButton>
              </div>
            </NDropdown>
          </div>
          <NButton size="small" type="error" secondary :disabled="!selectedIds.size" @click="handleDeleteBySelection">
            <template #icon>
              <SvgIcon
                :icon="selectedIds.size > 1 ? 'mdi:delete-sweep-outline' : 'mdi:delete-outline'"
                class="text-16px"
              />
            </template>
            {{ selectedIds.size > 1 ? '批量删除' : '删除' }}
          </NButton>
          <NTooltip trigger="hover">
            <template #trigger>
              <NButton size="small" secondary @click="handleCleanupInvalidRefs">
                <template #icon><SvgIcon icon="mdi:link-variant-off" class="text-16px" /></template>
                清理无效引用
              </NButton>
            </template>
            解除指向不存在业务对象的悬空引用（如已删除的商品）
          </NTooltip>
          <NButton
            v-if="selectedIds.size > 1"
            size="small"
            secondary
            :disabled="!selectedIds.size"
            @click="showMoveDialog"
          >
            <template #icon><SvgIcon icon="mdi:folder-move-outline" class="text-16px" /></template>
            移动到目录
          </NButton>
          <NButton
            v-if="selectedIds.size > 1"
            size="small"
            secondary
            :disabled="!selectedIds.size"
            @click="showTagDialog"
          >
            <template #icon><SvgIcon icon="mdi:tag-plus-outline" class="text-16px" /></template>
            批量打标
          </NButton>
          <input ref="fileInput" type="file" multiple class="hidden" @change="onFileChange" />
          <input ref="folderInput" type="file" webkitdirectory multiple class="hidden" @change="onFolderChange" />
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

      <!-- 缩略图网格（拖拽上传区） -->
      <div
        ref="gridScrollRef"
        class="relative flex-1 overflow-y-auto p-3"
        :class="dragActive ? 'bg-green-50/60 dark:bg-green-900/10' : ''"
        @dragover.prevent="dragActive = true"
        @dragleave.prevent="dragActive = false"
        @drop.prevent="onDrop"
      >
        <div
          v-if="dragActive"
          class="pointer-events-none absolute inset-0 z-30 flex items-center justify-center border-2 border-green-500 border-dashed rounded-xl bg-green-50/80 dark:bg-green-900/20"
        >
          <div class="flex flex-col items-center text-green-600">
            <SvgIcon icon="mdi:upload-multiple" class="text-44px mb-2" />
            <span class="text-sm font-medium">松开鼠标上传文件 / 文件夹</span>
          </div>
        </div>
        <div v-if="uploading" class="mb-3">
          <NProgress
            type="line"
            :percentage="Math.round((uploadDone / uploadTotal) * 100)"
            :show-indicator="false"
            :height="4"
            color="#22c55e"
          />
          <div class="mt-1 flex justify-between text-xs text-gray-500">
            <span>{{ uploadDone }} / {{ uploadTotal }}</span>
            <span>{{ uploadQueue > 0 ? '正在上传…' : '处理中…' }}</span>
          </div>
        </div>
        <div v-if="loading" class="flex h-full items-center justify-center text-gray-400">
          <NSpin size="small" />
          <span class="ml-2">资源加载中…</span>
        </div>
        <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-20 text-gray-400">
          <SvgIcon icon="mdi:image-off-outline" class="text-40px mb-2" />
          <span>暂无资源，点击右上角上传</span>
        </div>
        <div v-else class="grid h-full grid-cols-4 grid-rows-6 gap-3 xl:grid-cols-5">
          <div
            v-for="r in items"
            :key="r.id"
            draggable="true"
            class="group relative flex min-h-0 cursor-pointer flex-col overflow-hidden rounded-lg border border-gray-100 border-solid dark:border-gray-700"
            :class="
              currentDetail?.id === r.id
                ? 'ring-2 ring-green-500'
                : selectedIds.has(r.id)
                  ? 'ring-2 ring-green-400'
                  : ''
            "
            @click="selectedIds.size > 1 ? toggleSelect(r.id) : selectDetail(r)"
            @dragstart="onCardDragStart($event, r)"
          >
            <div class="flex min-h-0 flex-1 items-center justify-center bg-gray-50 dark:bg-gray-800">
              <img
                v-if="isPreviewableImage(r)"
                :src="r.thumb_url || r.url"
                :data-origin="r.url"
                class="h-full w-full object-cover"
                loading="lazy"
                decoding="async"
                @error="
                  e => {
                    const el = e.target as HTMLImageElement;
                    if (el.src !== el.dataset.origin) el.src = el.dataset.origin || '';
                  }
                "
              />
              <div v-else-if="isPreviewableVideo(r)" class="relative h-full w-full">
                <video :src="r.url" preload="metadata" muted playsinline class="h-full w-full object-cover" />
                <span class="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <SvgIcon icon="mdi:play-circle-outline" class="text-24px text-white/85 drop-shadow" />
                </span>
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
              class="absolute top-9 right-1.5 z-10 hidden h-6 w-6 cursor-zoom-in items-center justify-center rounded-full bg-black/50 text-white group-hover:flex hover:bg-black/70"
              @click.stop="openPreview(r)"
            >
              <SvgIcon icon="mdi:magnify-plus-outline" class="text-14px" />
            </div>
            <div class="truncate px-2 py-1.5 text-xs" :title="r.name">{{ r.name }}</div>
            <div v-if="r.tags?.length" class="flex flex-wrap gap-1 px-2 pb-1.5">
              <span
                v-for="t in r.tags.slice(0, 3)"
                :key="t"
                class="max-w-[80px] truncate rounded bg-blue-50 px-1 text-[10px] leading-4 text-blue-500 dark:bg-blue-900/30 dark:text-blue-300"
              >
                #{{ t }}
              </span>
              <span v-if="r.tags.length > 3" class="text-[10px] leading-4 text-gray-400">+{{ r.tags.length - 3 }}</span>
            </div>
            <div
              class="absolute top-1.5 right-1.5 z-20 flex h-5 w-5 cursor-pointer items-center justify-center rounded border border-solid text-xs transition-colors"
              :class="
                selectedIds.has(r.id)
                  ? 'border-green-500 bg-green-500 text-white'
                  : (r.ref_count ?? 0) > 0
                    ? 'border-orange-400 bg-orange-50 text-orange-500 dark:bg-orange-900/30'
                    : 'border-gray-300 bg-white text-gray-400 dark:border-gray-500 dark:bg-gray-700'
              "
              :title="(r.ref_count ?? 0) > 0 ? `被引用 ${r.ref_count} 处，不可删除` : '选择'"
              @click.stop="toggleSelect(r.id)"
            >
              <SvgIcon v-if="selectedIds.has(r.id)" icon="mdi:check" class="text-12px" />
            </div>
            <div
              v-if="(r.ref_count ?? 0) > 0"
              class="absolute bottom-1.5 left-1.5 z-10 rounded bg-orange-500/90 px-1 text-[10px] leading-4 text-white"
              title="被引用资源，不可删除"
            >
              引用 {{ r.ref_count }}
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div
        class="flex items-center justify-between border-t border-gray-100 border-solid px-4 py-2 dark:border-gray-700"
      >
        <span class="text-xs text-gray-500">共 {{ total }} 个资源</span>
        <NPagination :page="page" :page-size="pageSize" :item-count="total" size="small" @update:page="onPageChange" />
      </div>
    </div>

    <!-- 右：详情 -->
    <div class="flex w-[300px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <div class="border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700">
        <span class="text-sm font-semibold">{{ selectedIds.size > 1 ? '批量操作' : '资源详情' }}</span>
      </div>
      <div v-if="selectedIds.size > 1" class="flex flex-1 flex-col items-center justify-center gap-3 p-4">
        <SvgIcon icon="mdi:checkbox-multiple-marked-outline" class="text-40px text-green-500" />
        <span class="text-sm text-gray-600 dark:text-gray-300">已选中 {{ selectedIds.size }} 项</span>
        <div class="flex w-full flex-col gap-2">
          <NButton size="small" type="primary" secondary block @click="showMoveDialog">
            <template #icon><SvgIcon icon="mdi:folder-move-outline" class="text-14px" /></template>
            移动到目录
          </NButton>
          <NButton size="small" secondary block @click="showTagDialog">
            <template #icon><SvgIcon icon="mdi:tag-plus-outline" class="text-14px" /></template>
            批量打标
          </NButton>
          <NButton size="small" type="error" secondary block @click="handleDeleteBySelection">
            <template #icon><SvgIcon icon="mdi:delete-sweep-outline" class="text-14px" /></template>
            批量删除
          </NButton>
          <NButton size="small" block @click="selectedIds = new Set()">
            <template #icon><SvgIcon icon="mdi:close-circle-outline" class="text-14px" /></template>
            取消选择
          </NButton>
        </div>
      </div>
      <div v-else-if="currentDetail" class="flex-1 overflow-y-auto p-4">
        <!-- 预览 -->
        <div
          class="mb-3 flex h-[160px] cursor-zoom-in items-center justify-center overflow-hidden rounded bg-gray-50 dark:bg-gray-800"
          @click="openPreview(currentDetail)"
        >
          <img v-if="isPreviewableImage(currentDetail)" :src="currentDetail.url" class="h-full w-full object-contain" />
          <video
            v-else-if="isPreviewableVideo(currentDetail)"
            :src="currentDetail.url"
            controls
            class="h-full w-full"
          />
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
          <div class="flex justify-between">
            <span class="text-gray-500">类型</span>
            <span>{{ currentDetail.file_type }} / {{ currentDetail.mime }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">大小</span>
            <span>{{ formatSize(currentDetail.file_size) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">上传时间</span>
            <span>{{ formatTime(currentDetail.created_at) }}</span>
          </div>
          <div class="flex justify-between gap-2">
            <span class="text-gray-500 shrink-0">目录</span>
            <span class="truncate" :title="currentDetail.directory || '未归档'">
              {{ currentDetail.directory || '未归档' }}
            </span>
          </div>
          <div v-if="currentDetail.tags?.length" class="flex justify-between gap-2">
            <span class="text-gray-500 shrink-0">标签</span>
            <span class="flex flex-wrap justify-end gap-1">
              <span
                v-for="t in currentDetail.tags"
                :key="t"
                class="rounded bg-blue-50 px-1 text-[10px] leading-4 text-blue-500 dark:bg-blue-900/30 dark:text-blue-300"
              >
                #{{ t }}
              </span>
            </span>
          </div>
          <div class="flex justify-between gap-2">
            <span class="text-gray-500 shrink-0">MinIO 路径</span>
            <span class="truncate" :title="currentDetail.object_key || currentDetail.url">
              {{ currentDetail.object_key || '-' }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <div class="flex justify-between gap-2">
              <span class="text-gray-500 shrink-0">引用位置</span>
              <span v-if="!currentRefs.length" class="text-right">无引用</span>
            </div>
            <div v-for="(ref, idx) in currentRefs" :key="`${ref.ref_type}-${ref.ref_id}-${idx}`">
              <div
                v-if="canJumpRef(ref)"
                class="flex cursor-pointer items-center justify-between gap-2 rounded bg-gray-50 px-2 py-1 text-xs hover:bg-green-50 dark:bg-gray-800 dark:hover:bg-green-900/20"
                :title="`跳转到 ${ref.ref_label}`"
                @click="jumpToRef(ref)"
              >
                <span class="truncate">{{ ref.ref_label || ref.ref_type }}</span>
                <SvgIcon icon="mdi:open-in-new" class="text-13px shrink-0 text-green-500" />
              </div>
              <div
                v-else
                class="flex cursor-not-allowed items-center justify-between gap-2 rounded bg-gray-50 px-2 py-1 text-xs opacity-60 dark:bg-gray-800"
                :title="`ref_type=${ref.ref_type} 无对应路由`"
              >
                <span class="truncate">{{ ref.ref_label || ref.ref_type }}</span>
                <span
                  class="rounded bg-gray-200 px-1 text-[10px] leading-4 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                >
                  无路由
                </span>
              </div>
            </div>
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
          <div class="grid grid-cols-2 gap-2">
            <NButton size="small" @click="download(currentDetail)">
              <template #icon><SvgIcon icon="mdi:download" class="text-14px" /></template>
              下载
            </NButton>
            <NButton size="small" type="error" secondary @click="doDelete(currentDetail)">
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
      :title="
        previewType === 'image'
          ? '图片预览'
          : previewType === 'video'
            ? '视频预览'
            : previewType === 'audio'
              ? '音频预览'
              : previewType === 'pdf'
                ? 'PDF 预览'
                : previewType === 'docx'
                  ? 'Word 预览'
                  : previewType === 'md'
                    ? 'Markdown 预览'
                    : previewType === 'zip'
                      ? '压缩包内容'
                      : '资源预览'
      "
      style="width: 80%; max-width: 960px"
    >
      <div class="flex items-center justify-center">
        <img
          v-if="previewType === 'image'"
          :src="previewUrl"
          class="max-h-[70vh] max-w-full object-contain"
          alt="预览"
        />
        <video
          v-else-if="previewType === 'video'"
          :src="previewUrl"
          controls
          autoplay
          class="max-h-[70vh] max-w-full"
        />
        <audio v-else-if="previewType === 'audio'" :src="previewUrl" controls autoplay class="w-full" />
        <iframe v-else-if="previewType === 'pdf'" :src="previewUrl" class="h-[70vh] w-full rounded-md border" />
        <div
          v-else-if="previewType === 'docx'"
          ref="previewDocxRef"
          class="max-h-[70vh] w-full overflow-auto rounded-md border bg-white p-4 text-left"
        />
        <div
          v-else-if="previewType === 'md'"
          class="max-h-[70vh] w-full overflow-auto rounded-md border bg-white p-4 text-left"
          v-html="previewHtml"
        />
        <pre
          v-else-if="previewType === 'text'"
          class="max-h-[70vh] w-full overflow-auto rounded-md border bg-gray-50 p-4 text-left text-xs"
        >{{ previewText }}</pre>
        <div
          v-else-if="previewType === 'zip'"
          class="max-h-[70vh] w-full overflow-auto rounded-md border bg-gray-50 p-4 text-left text-sm"
        >
          <div v-if="zipLoading" class="text-gray-400">正在解析压缩包...</div>
          <ul v-else class="list-disc pl-5">
            <li v-for="f in zipFiles" :key="f">{{ f }}</li>
          </ul>
        </div>
        <div v-else class="flex flex-col items-center gap-2 py-10 text-gray-400">
          <SvgIcon icon="mdi:file-document-outline" class="text-60px" />
          <span class="text-sm">该类型暂不支持预览，可通过下载查看</span>
        </div>
      </div>
    </NModal>

    <NModal v-model:show="moveDialogVisible" preset="card" title="移动到目录" style="width: 420px">
      <NSelect
        v-model:value="moveTargetDir"
        clearable
        filterable
        placeholder="选择目录（留空=未归档）"
        :options="[
          { label: '未归档（根目录）', value: '' },
          ...Array.from(new Set(directories.map(d => d.directory).filter(Boolean))).map(d => ({ label: d, value: d }))
        ]"
      />
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="moveDialogVisible = false">取消</NButton>
          <NButton size="small" type="primary" @click="confirmMove">移动</NButton>
        </div>
      </template>
    </NModal>

    <NModal v-model:show="tagDialogVisible" preset="card" title="批量添加标签" style="width: 420px">
      <NInput v-model:value="tagInputValue" placeholder="多个标签用逗号或空格分隔，如：主图, banner" size="small" />
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="tagDialogVisible = false">取消</NButton>
          <NButton size="small" type="primary" @click="confirmTags">打标</NButton>
        </div>
      </template>
    </NModal>

    <!-- 回收站 -->
    <NModal v-model:show="trashVisible" preset="card" title="回收站" style="width: 720px">
      <div class="mb-3 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <NInput
            v-model:value="trashKeyword"
            placeholder="搜索名称"
            size="small"
            clearable
            style="width: 200px"
            @keyup.enter="onTrashSearch"
          >
            <template #prefix><SvgIcon icon="mdi:magnify" class="text-14px" /></template>
          </NInput>
          <NButton size="small" @click="onTrashSearch">搜索</NButton>
          <NButton size="small" type="primary" :disabled="!trashSelected.size" @click="restoreTrashSelection">
            <template #icon><SvgIcon icon="mdi:restore" class="text-14px" /></template>
            恢复选中（{{ trashSelected.size }}）
          </NButton>
          <NButton size="small" type="error" secondary :disabled="!trashSelected.size" @click="purgeTrashSelection">
            <template #icon><SvgIcon icon="mdi:delete-forever-outline" class="text-14px" /></template>
            彻底删除
          </NButton>
        </div>
        <NButton size="small" type="error" tertiary :disabled="!trashTotal" @click="emptyTrashAll">
          <template #icon><SvgIcon icon="mdi:delete-sweep-outline" class="text-14px" /></template>
          清空回收站
        </NButton>
      </div>
      <NSpin :show="trashLoading">
        <div
          v-if="!trashItems.length && !trashLoading"
          class="flex flex-col items-center justify-center py-16 text-gray-400"
        >
          <SvgIcon icon="mdi:delete-restore-outline" class="text-40px mb-2" />
          <span>回收站是空的</span>
        </div>
        <div v-else class="max-h-[46vh] overflow-y-auto">
          <div
            v-for="r in trashItems"
            :key="r.id"
            class="flex cursor-pointer items-center gap-3 rounded border border-gray-100 border-solid px-3 py-2 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
            :class="trashSelected.has(r.id) ? 'border-green-400 bg-green-50/50 dark:bg-green-900/10' : ''"
            @click="toggleTrashSelect(r.id)"
          >
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded bg-gray-100 dark:bg-gray-800"
            >
              <img
                v-if="isPreviewableImage(r)"
                :src="r.thumb_url || r.url"
                :data-origin="r.url"
                class="h-full w-full object-cover"
                loading="lazy"
                @error="
                  e => {
                    const el = e.target as HTMLImageElement;
                    if (el.src !== el.dataset.origin) el.src = el.dataset.origin || '';
                  }
                "
              />
              <video
                v-else-if="isPreviewableVideo(r)"
                :src="r.url"
                preload="metadata"
                muted
                playsinline
                class="h-full w-full object-cover"
              />
              <SvgIcon v-else-if="isPreviewableAudio(r)" icon="mdi:music-note" class="text-20px text-gray-400" />
              <SvgIcon v-else icon="mdi:file-document-outline" class="text-20px text-gray-400" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm">{{ r.name }}</div>
              <div class="text-xs text-gray-400">
                {{ r.directory ? `目录：${r.directory}` : '未归档' }} · {{ formatSize(r.file_size) }}
              </div>
            </div>
            <div class="shrink-0 text-xs text-gray-400">删除于 {{ (r.deleted_at || '').slice(0, 10) }}</div>
            <NButton size="tiny" quaternary @click.stop="openPreview(r)">
              <template #icon><SvgIcon icon="mdi:magnify-plus-outline" class="text-14px" /></template>
            </NButton>
          </div>
        </div>
      </NSpin>
      <template #footer>
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-500">共 {{ trashTotal }} 个</span>
          <NPagination
            :page="trashPage"
            :page-size="trashPageSize"
            :item-count="trashTotal"
            size="small"
            @update:page="onTrashPageChange"
          />
        </div>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.hidden {
  display: none;
}
</style>

<style>
/* 上传文件夹下拉菜单：去边框、尺寸与「上传」按钮对齐（teleport 到 body，需全局样式） */
.upload-folder-menu .n-dropdown-menu {
  padding: 0;
  border: none !important;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}
.upload-folder-menu .n-dropdown-option {
  min-width: 80px;
  height: 28px;
}
.upload-folder-menu .n-dropdown-option-body {
  justify-content: center;
  padding: 0 6px;
  white-space: nowrap;
}
</style>
