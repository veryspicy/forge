<template>
  <div class="site-config-page flex h-full gap-0" style="min-height: calc(100vh - 180px)">
    <!-- 左侧面板：站点配置列表 -->
    <div v-if="leftPanelVisible" class="flex w-[260px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <div class="flex items-center gap-2 border-b border-gray-100 border-solid px-4 py-3 dark:border-gray-700">
        <SvgIcon icon="mdi:cog-outline" class="text-18px text-green-600" />
        <span class="text-sm font-semibold">站点配置</span>
      </div>
      <div class="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
        <div
          v-for="item in siteConfigItems"
          :key="item.key"
          class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors"
          :class="store.activeSiteConfigItem === item.key
            ? 'bg-green-50 text-green-700 font-medium dark:bg-green-900/20 dark:text-green-400'
            : 'hover:bg-gray-50 dark:hover:bg-gray-800'"
          @click="store.selectSiteConfigItem(item.key)"
        >
          <SvgIcon :icon="item.icon" class="text-14px shrink-0" />
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>

    <!-- 中间区域：预览 iframe -->
    <div class="flex flex-1 flex-col overflow-hidden rounded bg-white dark:bg-dark">
      <!-- 顶栏：面板切换 + URL + 设备切换 + 元素选择 -->
      <div class="flex items-center justify-between border-b border-gray-100 border-solid px-4 py-2 dark:border-gray-700">
        <div class="flex items-center gap-2">
          <NButton size="small" quaternary @click="leftPanelVisible = !leftPanelVisible">
            <template #icon>
              <SvgIcon :icon="leftPanelVisible ? 'mdi:chevron-double-left' : 'mdi:chevron-double-right'" class="text-16px" />
            </template>
          </NButton>
          <NTooltip trigger="hover">
            <template #trigger>
              <NButton size="small" quaternary @click="openInBrowser">
                <template #icon><SvgIcon icon="mdi:open-in-new" class="text-16px" /></template>
              </NButton>
            </template>
            在浏览器中打开
          </NTooltip>
          <NTooltip trigger="hover">
            <template #trigger>
              <NButton size="small" quaternary :type="elementSelectMode ? 'primary' : 'default'" @click="toggleElementSelect">
                <template #icon><SvgIcon icon="mdi:cursor-default-click" class="text-16px" /></template>
              </NButton>
            </template>
            开启选择元素模式
          </NTooltip>
          <NTooltip trigger="hover">
            <template #trigger>
              <NButton size="small" quaternary @click="refreshIframe">
                <template #icon><SvgIcon icon="mdi:refresh" class="text-16px" /></template>
              </NButton>
            </template>
            刷新预览 iframe
          </NTooltip>
        </div>
        <div class="flex items-center gap-1">
          <NButton size="small" :type="device === 'desktop' ? 'primary' : 'default'" quaternary @click="device = 'desktop'">
            <template #icon><SvgIcon icon="mdi:monitor" /></template>
          </NButton>
          <NButton size="small" :type="device === 'tablet' ? 'primary' : 'default'" quaternary @click="device = 'tablet'">
            <template #icon><SvgIcon icon="mdi:tablet" /></template>
          </NButton>
          <NButton size="small" :type="device === 'mobile' ? 'primary' : 'default'" quaternary @click="device = 'mobile'">
            <template #icon><SvgIcon icon="mdi:cellphone" /></template>
          </NButton>
        </div>
        <NButton size="small" quaternary @click="panelVisible = !panelVisible">
          <template #icon>
            <SvgIcon :icon="panelVisible ? 'mdi:chevron-double-right' : 'mdi:chevron-double-left'" class="text-16px" />
          </template>
        </NButton>
      </div>

      <!-- iframe 预览 -->
      <div class="flex-1 overflow-hidden">
        <div class="h-full flex justify-center overflow-auto bg-gray-100 p-0 dark:bg-true-gray-900">
          <div class="overflow-hidden bg-white shadow-lg transition-all duration-300" :class="deviceFrameClass">
            <iframe
              :key="iframeKey"
              ref="iframeRef"
              :src="iframeSrc"
              class="h-full w-full border-none"
              sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox"
              @load="onIframeLoad"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧拖拽分隔条 -->
    <div
      v-if="panelVisible"
      class="group flex w-1 shrink-0 cursor-col-resize items-center justify-center bg-transparent"
      title="拖拽调整面板宽度 (260~520px)"
      @mousedown="startPanelResize"
    >
      <div class="h-10 w-0.5 rounded bg-gray-200 transition-colors group-hover:bg-green-400 dark:bg-gray-700" />
    </div>

    <!-- 右侧面板：站点配置编辑表单 / 选中元素信息 -->
    <div v-if="panelVisible" class="shrink-0 overflow-hidden" :style="{ width: panelWidth + 'px' }">
      <PropertyPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { NButton, NTooltip } from 'naive-ui';
import { useDiyStore, SITE_CONFIG_ITEMS } from '@/store/modules/diy';
import PropertyPanel from './modules/PropertyPanel.vue';

const store = useDiyStore();
const siteConfigItems = SITE_CONFIG_ITEMS;

// ========== 左右面板可见性 ==========
const leftPanelVisible = ref(true);
const panelVisible = ref(false);
/** 右侧属性面板宽度（可拖拽调整，260~520px） */
const panelWidth = ref(300);
const PANEL_WIDTH_MIN = 260;
const PANEL_WIDTH_MAX = 520;

/** 开始拖拽右侧面板分隔条（rAF 节流，避免每帧更新响应式导致卡顿） */
let panelResizeRaf = 0;
function startPanelResize(e: MouseEvent) {
  e.preventDefault();
  const startX = e.clientX;
  const startWidth = panelWidth.value;
  function onMove(ev: MouseEvent) {
    const delta = startX - ev.clientX;
    const next = Math.min(PANEL_WIDTH_MAX, Math.max(PANEL_WIDTH_MIN, startWidth + delta));
    if (panelResizeRaf) cancelAnimationFrame(panelResizeRaf);
    panelResizeRaf = requestAnimationFrame(() => {
      panelWidth.value = next;
      panelResizeRaf = 0;
    });
  }
  function onUp() {
    if (panelResizeRaf) {
      cancelAnimationFrame(panelResizeRaf);
      panelResizeRaf = 0;
    }
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
}

/** 选中左侧配置项或元素时自动打开右侧面板 */
watch(
  () => [store.activeSiteConfigItem, store.selectedElement],
  ([configKey, element]) => {
    if (configKey || element) panelVisible.value = true;
  }
);

// ========== iframe 预览 ==========
const iframeRef = ref<HTMLIFrameElement | null>(null);
const iframeKey = ref(0);
const iframeSrc = ref('/zh?preview=true');
const device = ref<'desktop' | 'tablet' | 'mobile'>('desktop');

const deviceFrameClass = computed(() => {
  if (device.value === 'desktop') return 'w-full h-full';
  if (device.value === 'tablet') return 'w-[768px] h-[1024px]';
  return 'w-[390px] h-[844px]';
});

/** iframe 加载完成后：初始化元素选择模式 */
function onIframeLoad() {
  nextTick(() => {
    installElementSelect();
  });
}

/** 在浏览器新窗口打开当前预览页 */
function openInBrowser() {
  window.open(iframeSrc.value, '_blank');
}

/** 刷新 iframe 预览（强制重新加载 C 端） */
function refreshIframe() {
  iframeKey.value += 1;
}

// ========== 元素选择模式 ==========
const elementSelectMode = ref(false);
/** 当前安装的元素选择 cleanup 函数 */
let selectCleanup: (() => void) | null = null;
/** 全局 hover/selected class 清理 */
let globalCleanup: (() => void) | null = null;

function toggleElementSelect() {
  elementSelectMode.value = !elementSelectMode.value;
  store.setElementSelectMode(elementSelectMode.value);
  if (elementSelectMode.value) {
    installElementSelect();
  } else {
    uninstallElementSelect();
    store.setSelectedElement(null);
  }
}

/** 清除元素 hover/selected 高亮 class */
function clearAllHighlights(doc: Document) {
  doc.querySelectorAll('.marvis-hover, .marvis-selected').forEach(el => {
    el.classList.remove('marvis-hover', 'marvis-selected');
  });
}

/** 安装元素选择模式：监听 iframe 内点击/hover 事件 */
function installElementSelect() {
  uninstallElementSelect();
  const iframe = iframeRef.value;
  if (!iframe || !iframe.contentDocument) return;
  const doc = iframe.contentDocument;

  // 注入高亮样式
  const style = doc.createElement('style');
  style.id = 'marvis-select-style';
  style.textContent = `
    .marvis-hover { outline: 2px dashed #18a058 !important; outline-offset: -2px; cursor: pointer !important; }
    .marvis-selected { outline: 2px solid #ff6b6b !important; outline-offset: -2px; }
  `;
  doc.head.appendChild(style);

  let currentHover: HTMLElement | null = null;
  let currentSelected: HTMLElement | null = null;

  function clearHover() {
    if (currentHover) {
      currentHover.classList.remove('marvis-hover');
      currentHover = null;
    }
  }

  function clearSelected() {
    if (currentSelected) {
      currentSelected.classList.remove('marvis-selected');
      currentSelected = null;
    }
  }

  function handleMouseOver(e: Event) {
    if (!elementSelectMode.value) return;
    const target = (e.target as HTMLElement);
    if (!target || target === doc.body || target === doc.documentElement) return;
    if (currentHover && currentHover !== target) {
      currentHover.classList.remove('marvis-hover');
    }
    currentHover = target;
    currentHover.classList.add('marvis-hover');
  }

  function handleMouseOut() {
    if (currentHover) {
      currentHover.classList.remove('marvis-hover');
      currentHover = null;
    }
  }

  function handleClick(e: MouseEvent) {
    if (!elementSelectMode.value) return;
    e.preventDefault();
    e.stopPropagation();
    const target = (e.target as HTMLElement);
    if (!target) return;

    // 清除之前选中
    if (currentSelected) {
      currentSelected.classList.remove('marvis-selected');
    }
    currentSelected = target;
    currentSelected.classList.add('marvis-selected');

    // 提取元素信息并同步到 store
    const rect = target.getBoundingClientRect();
    const cs = window.getComputedStyle(target);
    const elid = (target.dataset.marvisElid || (crypto.randomUUID?.() || genId())) as string;
    target.dataset.marvisElid = elid;

    const info = {
      elid,
      selector: buildSelector(target, doc),
      tag: target.tagName,
      id: target.id || '',
      classes: Array.from(target.classList).filter(c => !c.startsWith('marvis-')),
      textContent: (target.textContent || '').trim().slice(0, 100),
      rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
      computedStyles: {
        color: cs.color,
        backgroundColor: cs.backgroundColor,
        fontSize: cs.fontSize,
        fontWeight: cs.fontWeight,
        textAlign: cs.textAlign,
        lineHeight: cs.lineHeight,
        padding: cs.padding,
        margin: cs.margin,
        border: cs.border,
        borderRadius: cs.borderRadius
      }
    };
    store.setSelectedElement(info);
  }

  function buildSelector(el: HTMLElement, d: Document): string {
    if (el.id) return `#${el.id}`;
    const parts: string[] = [];
    let cur: HTMLElement | null = el;
    while (cur && cur !== d.body && cur !== d.documentElement) {
      let seg = cur.tagName.toLowerCase();
      if (cur.classList.length > 0) {
        seg += '.' + Array.from(cur.classList).filter(c => !c.startsWith('marvis-')).join('.');
      }
      const parent = cur.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === cur!.tagName);
        if (siblings.length > 1) {
          seg += `:nth-child(${siblings.indexOf(cur) + 1})`;
        }
      }
      parts.unshift(seg);
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  }

  function genId(): string {
    return 'el-' + Math.random().toString(36).slice(2, 10);
  }

  doc.addEventListener('mouseover', handleMouseOver, true);
  doc.addEventListener('mouseout', handleMouseOut, true);
  doc.addEventListener('click', handleClick, true);

  selectCleanup = () => {
    clearHover();
    clearSelected();
    clearAllHighlights(doc);
    doc.removeEventListener('mouseover', handleMouseOver, true);
    doc.removeEventListener('mouseout', handleMouseOut, true);
    doc.removeEventListener('click', handleClick, true);
    style.remove();
  };
}

function uninstallElementSelect() {
  if (selectCleanup) {
    selectCleanup();
    selectCleanup = null;
  }
}

// 切换 tab/page 时重新安装（虽然本页只有首页预览，保留以防扩展）
watch(iframeKey, () => {
  if (elementSelectMode.value) {
    nextTick(() => installElementSelect());
  }
});

// ========== 生命周期 ==========
onMounted(async () => {
  await store.fetchSiteConfig();
});

onActivated(() => {
  if (elementSelectMode.value) {
    nextTick(() => installElementSelect());
  }
});

onBeforeUnmount(() => {
  uninstallElementSelect();
  if (globalCleanup) {
    globalCleanup();
    globalCleanup = null;
  }
});
</script>
