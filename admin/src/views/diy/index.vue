<template>
  <div class="diy-decoration flex h-full gap-0" style="min-height: calc(100vh - 180px)">
    <!-- 左侧面板：页面列表 + 站点配置 + 组件库（统一折叠） -->
    <div v-if="leftPanelVisible" class="flex w-[280px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <NCollapse :default-expanded-names="['pages', 'components']" class="left-collapse flex-1">
        <!-- 页面（Tab 形式：首页固定 + 动态打开的标签） -->
        <NCollapseItem name="pages">
          <template #header>
            <div class="flex w-full items-center justify-between">
              <div class="flex items-center gap-2">
                <SvgIcon icon="mdi:file-document-multiple-outline" class="text-16px text-blue-600" />
                <span class="text-sm font-semibold">页面</span>
              </div>
              <NButton size="tiny" quaternary type="primary" @click.stop="showCreate = true">
                <template #icon><SvgIcon icon="mdi:plus" /></template>
              </NButton>
            </div>
          </template>
          <div class="flex flex-col gap-1 px-1">
            <div
              v-for="tab in store.openTabs"
              :key="tab.id"
              class="group flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors"
              :class="store.activeTabId === tab.id
                ? 'bg-primary/10 text-primary font-medium'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800'"
              @click="handleTabClick(tab)"
            >
              <SvgIcon :icon="pageIcon(tab.page_type)" class="text-16px shrink-0" />
              <span class="truncate flex-1">{{ tab.name }}</span>
              <NTag
                v-if="tab.status && tab.status !== 'not_initialized'"
                :bordered="false"
                size="tiny"
                :type="tab.status === 'published' ? 'success' : 'default'"
                class="shrink-0"
              >
                {{ tab.status === 'published' ? '已发布' : '草稿' }}
              </NTag>
              <NButton
                v-if="!tab.isPinned"
                size="tiny"
                quaternary
                type="error"
                class="shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
                @click.stop="handleTabClose(tab.id)"
              >
                <template #icon><SvgIcon icon="mdi:close" /></template>
              </NButton>
            </div>
          </div>
        </NCollapseItem>

        <!-- 站点配置 -->
        <NCollapseItem name="site-config">
          <template #header>
            <div class="flex items-center gap-2">
              <SvgIcon icon="mdi:cog-outline" class="text-16px text-green-600" />
              <span class="text-sm font-semibold">站点配置</span>
            </div>
          </template>
          <div class="flex flex-col gap-1 px-1">
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
        </NCollapseItem>

        <!-- 组件库 -->
        <NCollapseItem name="components">
          <template #header>
            <div class="flex items-center gap-2">
              <SvgIcon icon="mdi:widgets-outline" class="text-16px text-purple-600" />
              <span class="text-sm font-semibold">组件库</span>
            </div>
          </template>
          <div class="overflow-y-auto" style="max-height: calc(100vh - 360px)">
            <ComponentPanel />
          </div>
        </NCollapseItem>
      </NCollapse>
    </div>

    <!-- 中间区域：预览 + 画布 -->
    <div class="flex flex-1 flex-col overflow-hidden rounded bg-white dark:bg-dark">
      <!-- 顶栏：模式切换 + URL + 设备切换 -->
      <div class="flex items-center justify-between border-b px-4 py-2">
        <div class="flex items-center gap-2">
          <NButton size="small" quaternary @click="leftPanelVisible = !leftPanelVisible">
            <template #icon>
              <SvgIcon :icon="leftPanelVisible ? 'mdi:chevron-double-left' : 'mdi:chevron-double-right'" class="text-16px" />
            </template>
          </NButton>
          <NButtonGroup size="small">
            <NButton :type="mode === 'preview' ? 'primary' : 'default'" @click="switchMode('preview')">
              <template #icon><SvgIcon icon="mdi:eye" /></template>
              实时预览
            </NButton>
            <NButton :type="mode === 'canvas' ? 'primary' : 'default'" @click="switchMode('canvas')">
              <template #icon><SvgIcon icon="mdi:code-tags" /></template>
              结构编辑
            </NButton>
          </NButtonGroup>

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
        <div class="flex shrink-0 items-center gap-2">
          <NButton size="small" :loading="saving" @click="handleSave">{{ $t('common.saveDraft') }}</NButton>
          <NButton size="small" type="primary" :loading="publishing" @click="handlePublish">{{ $t('common.publish') }}</NButton>
          <NButton size="small" quaternary @click="panelVisible = !panelVisible">
            <template #icon>
              <SvgIcon :icon="panelVisible ? 'mdi:chevron-double-right' : 'mdi:chevron-double-left'" class="text-16px" />
            </template>
          </NButton>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="flex-1 overflow-hidden">
        <!-- 实时预览模式 -->
        <div v-if="mode === 'preview'" class="h-full flex justify-center overflow-auto bg-gray-100 p-0 dark:bg-true-gray-900">
          <div
            class="overflow-hidden bg-white shadow-lg transition-all duration-300"
            :class="deviceFrameClass"
          >
            <iframe
              :key="iframeKey"
              ref="iframeRef"
              :src="iframeSrc"
              class="h-full w-full border-none"
              sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
              @load="onIframeLoad"
            />
          </div>
        </div>

        <!-- 结构编辑模式（组件画布） -->
        <div v-else class="h-full flex justify-center overflow-y-auto bg-gray-100 p-0 dark:bg-true-gray-900">
          <div class="phone-frame w-[390px] min-h-[844px] shrink-0 overflow-hidden self-start rounded-xl bg-white shadow-lg">
            <VueDraggable
              v-model="pageComponents"
              :animation="200"
              ghost-class="ghost"
              handle=".drag-handle"
              :group="{ name: 'diy', pull: true, put: true }"
              item-key="id"
              class="min-h-[844px]"
              @add="onCanvasAdd"
              @end="onCanvasDragEnd"
            >
              <div
                v-for="pc in pageComponents"
                :key="pc.id"
                class="cursor-pointer"
                :class="{ 'ring-2 ring-primary': pc.id === store.activeComponentId }"
                @click="store.selectComponent(pc.id)"
              >
                <div class="flex items-center justify-between bg-gray-50 px-2 py-1 text-xs text-gray-400 drag-handle cursor-move">
                  <span>{{ pc.component_name }}</span>
                  <NButton size="tiny" quaternary type="error" @click.stop="store.removeComponent(pc.id)">
                    <template #icon><SvgIcon icon="mdi:close" /></template>
                  </NButton>
                </div>
                <component :is="getRenderer(pc.component_code)" :config="pc.config" />
              </div>
            </VueDraggable>
            <div
              v-if="!pageComponents.length"
              class="pointer-events-none flex h-[844px] flex-col items-center justify-center gap-2 text-gray-300"
            >
              <SvgIcon icon="mdi:gesture-tap" class="text-48px" />
              <span>从左侧组件库点击或拖入组件</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧面板：属性配置 -->
    <div v-if="panelVisible" class="w-[280px] shrink-0 overflow-hidden">
      <PropertyPanel />
    </div>

    <!-- 新建页面弹窗 -->
    <NModal v-model:show="showCreate" preset="card" title="新建页面" style="width:420px">
      <NForm label-placement="left" label-width="70px">
        <NFormItem label="名称" required>
          <NInput v-model:value="createForm.name" placeholder="如：关于我们" />
        </NFormItem>
        <NFormItem label="Slug" required>
          <NInput v-model:value="createForm.slug" placeholder="如：about-us" />
        </NFormItem>
        <NFormItem label="类型">
          <NSelect v-model:value="createForm.page_type" :options="typeOptions" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="handleCreate">确认</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import {
  NButton,
  NButtonGroup,
  NCollapse,
  NCollapseItem,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NTag,
  NTooltip
} from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { useDiyStore, SITE_CONFIG_ITEMS } from '@/store/modules/diy';
import type { DiyTabItem } from '@/store/modules/diy';
import { diyApi } from '@/service/api/diy';

const siteConfigItems = SITE_CONFIG_ITEMS;
import ComponentPanel from '@/views/diy-editor/modules/ComponentPanel.vue';
import PropertyPanel from '@/views/diy-editor/modules/PropertyPanel.vue';

// 导入所有渲染器
import BannerRenderer from '@/views/diy-editor/modules/renderers/BannerRenderer.vue';
import SearchBoxRenderer from '@/views/diy-editor/modules/renderers/SearchBoxRenderer.vue';
import ImageAdRenderer from '@/views/diy-editor/modules/renderers/ImageAdRenderer.vue';
import TextBlockRenderer from '@/views/diy-editor/modules/renderers/TextBlockRenderer.vue';
import RichTextRenderer from '@/views/diy-editor/modules/renderers/RichTextRenderer.vue';
import VideoRenderer from '@/views/diy-editor/modules/renderers/VideoRenderer.vue';
import DividerRenderer from '@/views/diy-editor/modules/renderers/DividerRenderer.vue';
import BlankRenderer from '@/views/diy-editor/modules/renderers/BlankRenderer.vue';
import GoodsListRenderer from '@/views/diy-editor/modules/renderers/GoodsListRenderer.vue';
import GoodsSingleRenderer from '@/views/diy-editor/modules/renderers/GoodsSingleRenderer.vue';
import GoodsGroupRenderer from '@/views/diy-editor/modules/renderers/GoodsGroupRenderer.vue';
import CouponRenderer from '@/views/diy-editor/modules/renderers/CouponRenderer.vue';
import CountdownRenderer from '@/views/diy-editor/modules/renderers/CountdownRenderer.vue';
import NoticeBarRenderer from '@/views/diy-editor/modules/renderers/NoticeBarRenderer.vue';
import NavGroupRenderer from '@/views/diy-editor/modules/renderers/NavGroupRenderer.vue';

const store = useDiyStore();

// --- 页面 Tab + 状态 ---
const mode = ref<'preview' | 'canvas'>('preview');
const device = ref<'desktop' | 'tablet' | 'mobile'>('desktop');
const saving = ref(false);
const publishing = ref(false);
const leftPanelVisible = ref(true);
const panelVisible = ref(false);
const iframeRef = ref<HTMLIFrameElement | null>(null);
const elementSelectMode = ref(false);
/** iframe src 手动控制：仅在 Tab 点击/关闭/初始化时更新，避免 iframe SPA 导航 → tab 创建 → previewUrl 变化 → iframe 重载 的反馈循环 */
const iframeSrc = ref('');
/** iframe key：每次 Tab 切换时递增，强制 iframe 重建（解决 SPA 导航后点击同 URL Tab 不触发导航的问题） */
const iframeKey = ref(0);
/** 缓存全量页面（system+custom）：用于根据 slug 查 custom 页面做动态 tab 回显 */
const allPagesCache = ref<any[]>([]);
let urlPollTimer: number | null = null;
let lastIframePath = '';

const deviceFrameClass = computed(() => ({
  'w-full': device.value === 'desktop',
  'w-[768px]': device.value === 'tablet',
  'w-[390px]': device.value === 'mobile'
}));

const pageIcon = (pageType: string) => {
  const map: Record<string, string> = {
    home: 'mdi:home',
    category: 'mdi:shape',
    product_detail: 'mdi:package-variant',
    custom: 'mdi:file-document'
  };
  return map[pageType] || 'mdi:file-document';
};

const pageTypeName = (pageType: string, slug?: string) => {
  const map: Record<string, string> = {
    home: '首页',
    category: '分类页',
    product_detail: '商品详情'
  };
  if (pageType === 'custom') return slug ? (allPagesCache.value.find(p => p.slug === slug)?.name || slug) : '自定义页';
  return map[pageType] || pageType;
};

/** 根据 tab 生成预览 URL（拼代理路径 + i18n 前缀 + preview=true） */
function buildPreviewUrl(tab: DiyTabItem | null | undefined): string {
  const base = '/portal-preview/zh';
  if (!tab) return `${base}?preview=true`;
  if (tab.page_type === 'home') return `${base}?preview=true`;
  if (tab.page_type === 'category') return `${base}/category/${tab.slug || 'all'}?preview=true`;
  if (tab.page_type === 'product_detail') return `${base}/products/${tab.slug || 'demo'}?preview=true`;
  return `${base}/${tab.slug}?preview=true`;
}

/** 当前选中 tab 对应预览 URL（用于 openInBrowser 等，不绑定到 iframe src） */
const previewUrl = computed(() => {
  const tab = store.openTabs.find(t => t.id === store.activeTabId);
  return buildPreviewUrl(tab);
});

async function loadPagesAndInitTabs() {
  try {
    const res = await diyApi.listPages();
    const all = res.data?.items || [];
    allPagesCache.value = all;
    // 找到首页并固定为第一个 tab
    const home = all.find((p: any) => p.page_type === 'home');
    if (home) {
      store.initTabs({
        id: home.id,
        name: home.name || '首页',
        page_type: home.page_type,
        slug: home.slug,
        status: home.status,
        components_count: home.components_count
      });
      // 默认加载首页内容
      store.reset();
      await Promise.all([
        store.fetchComponentsLibrary(),
        store.fetchPage(home.id)
      ]);
    } else {
      store.initTabs({
        id: 'home',
        name: '首页',
        page_type: 'home',
        slug: 'home',
        status: 'not_initialized'
      });
    }
    // 初始化 iframe src（仅此处设置一次，后续由 tab 点击/关闭手动控制）
    iframeSrc.value = buildPreviewUrl(store.pinnedHome);
    iframeKey.value++;
  } catch {
    allPagesCache.value = [];
  }
}

/** 点击 Tab 切换页面 */
async function handleTabClick(tab: any) {
  if (store.activeTabId === tab.id) return;
  store.activateTab(tab.id);
  // 先更新 iframe src，确保即时响应（不等待 fetchPage 完成）
  iframeSrc.value = buildPreviewUrl(tab);
  iframeKey.value++;
  store.reset();
  try {
    await store.fetchPage(tab.id);
  } catch { /* 页面未初始化时 fetch 失败，不影响 tab 切换 */ }
  // 切换 tab 后重新安装选择模式（如已开启）
  if (elementSelectMode.value) {
    setTimeout(() => {
      if (globalMarvisCleanup) { globalMarvisCleanup(); globalMarvisCleanup = null; }
      if (canvasMarvisCleanup) { canvasMarvisCleanup(); canvasMarvisCleanup = null; }
      if (mode.value === 'preview') installIframeSelection();
      else installCanvasSelection();
    }, 100);
  }
}

/** 关闭 Tab（首页不可关）。关闭当前页会切回首页。 */
async function handleTabClose(id: string) {
  const wasActive = store.activeTabId === id;
  const nextId = store.closeTab(id);
  if (wasActive && nextId) {
    // 先更新 iframe src，确保即时响应
    const nextTab = store.openTabs.find(t => t.id === nextId);
    iframeSrc.value = buildPreviewUrl(nextTab);
    iframeKey.value++;
    store.reset();
    try {
      await store.fetchPage(nextId);
    } catch { /* 页面未初始化时 fetch 失败，不影响 tab 切换 */ }
    if (elementSelectMode.value) {
      setTimeout(() => {
        if (globalMarvisCleanup) { globalMarvisCleanup(); globalMarvisCleanup = null; }
        if (canvasMarvisCleanup) { canvasMarvisCleanup(); canvasMarvisCleanup = null; }
        if (mode.value === 'preview') installIframeSelection();
        else installCanvasSelection();
      }, 100);
    }
  }
}

function switchMode(m: 'preview' | 'canvas') {
  mode.value = m;
}

function openInBrowser() {
  window.open(previewUrl.value, '_blank');
}

let globalMarvisCleanup: (() => void) | null = null;
let canvasMarvisCleanup: (() => void) | null = null;
let marvisFloatEl: HTMLElement | null = null;

function createMarvisFloatButton(tip: string, onToggle: () => void) {
  if (marvisFloatEl) marvisFloatEl.remove();
  const btn = document.createElement('div');
  btn.className = 'marvis-float-toggle';
  btn.innerHTML = `<div class="marvis-float-inner" title="${tip}"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11V5a1 1 0 0 1 1-1h0a1 1 0 0 1 1 1v11h0v-7"/><path d="M13 11V7a1 1 0 0 1 1-1h0a1 1 0 0 1 1 1v9h0v-5"/><path d="M5 15V3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v12a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3Z"/></svg><span class="marvis-float-tip">${tip}</span></div>`;
  Object.assign(btn.style, {
    position: 'fixed', top: '60px', right: '16px', zIndex: '99999',
    padding: '6px 10px', borderRadius: '10px', cursor: 'pointer',
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff',
    boxShadow: '0 6px 16px rgba(99,102,241,0.35)', fontSize: '13px', fontWeight: 500,
    display: 'flex', alignItems: 'center', gap: '6px', userSelect: 'none'
  });
  const tipEl = btn.querySelector('.marvis-float-tip') as HTMLElement;
  tipEl.style.marginLeft = '4px';
  btn.addEventListener('mouseenter', () => { btn.style.transform = 'translateY(-1px)'; btn.style.boxShadow = '0 8px 20px rgba(99,102,241,0.45)'; });
  btn.addEventListener('mouseleave', () => { btn.style.transform = ''; btn.style.boxShadow = '0 6px 16px rgba(99,102,241,0.35)'; });
  btn.addEventListener('click', e => { e.stopPropagation(); onToggle(); });
  document.body.appendChild(btn);
  marvisFloatEl = btn;
  return btn;
}

function removeMarvisFloatButton() {
  if (marvisFloatEl) {
    marvisFloatEl.remove();
    marvisFloatEl = null;
  }
}

function updateMarvisFloatTip(tip: string) {
  if (!marvisFloatEl) return;
  const tipEl = marvisFloatEl.querySelector('.marvis-float-tip') as HTMLElement;
  if (tipEl) tipEl.textContent = tip;
  marvisFloatEl.title = tip;
}

function installMarvisOnDoc(doc: Document, win: Window, isIframe: boolean) {
  const existingStyle = doc.getElementById('marvis-element-select');
  if (existingStyle) existingStyle.remove();

  const style = doc.createElement('style');
  style.id = 'marvis-element-select';
  style.textContent = `
    .marvis-hover-highlight{
      outline: 2px solid #ef4444 !important;
      outline-offset: 0px;
      box-shadow: inset 0 0 0 2px #10b981 !important;
    }
    .marvis-selected-highlight{
      outline: 3px solid #dc2626 !important;
      outline-offset: 0px;
      box-shadow: inset 0 0 0 3px #14b8a6 !important;
    }
    .marvis-tag-badge{
      position: fixed;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      background: #10b981;
      color: #fff;
      font-size: 11px;
      font-weight: 600;
      border-radius: 0 0 6px 0;
      pointer-events: none;
      z-index: 2147483646;
      letter-spacing: 0.3px;
      box-shadow: 0 2px 6px rgba(16,185,129,0.4);
    }
    .marvis-tag-badge.selected{
      background: #dc2626;
      box-shadow: 0 2px 6px rgba(220,38,38,0.45);
    }
    body.marvis-selecting-mode *{
      cursor: crosshair !important;
    }
  `;
  doc.head.appendChild(style);

  doc.body.classList.add('marvis-selecting-mode');

  let currentHover: HTMLElement | null = null;
  let currentSelected: HTMLElement | null = null;
  let hoverBadge: HTMLElement | null = null;
  let selectedBadge: HTMLElement | null = null;
  let destroyed = false;

  function getRect(el: HTMLElement) {
    return el.getBoundingClientRect();
  }

  function ensureBadge(type: 'hover' | 'selected') {
    let badge = type === 'hover' ? hoverBadge : selectedBadge;
    if (!badge) {
      badge = doc.createElement('div');
      badge.className = 'marvis-tag-badge' + (type === 'selected' ? ' selected' : '');
      doc.body.appendChild(badge);
      if (type === 'hover') hoverBadge = badge;
      else selectedBadge = badge;
    }
    return badge;
  }

  function removeBadge(type: 'hover' | 'selected') {
    if (type === 'hover' && hoverBadge) {
      hoverBadge.remove();
      hoverBadge = null;
    }
    if (type === 'selected' && selectedBadge) {
      selectedBadge.remove();
      selectedBadge = null;
    }
  }

  function positionBadge(el: HTMLElement, type: 'hover' | 'selected') {
    const badge = ensureBadge(type);
    badge.textContent = el.tagName.toLowerCase();
    const r = getRect(el);
    const scrollX = win.scrollX || 0;
    const scrollY = win.scrollY || 0;
    Object.assign((badge as HTMLElement).style, {
      top: Math.max((isIframe ? 0 : r.top), 0) + (isIframe ? r.top : 0) + 'px',
      left: (isIframe ? r.left : r.left) + 'px'
    });
  }

  function clearHover() {
    if (currentHover) {
      currentHover.classList.remove('marvis-hover-highlight');
    }
    currentHover = null;
    removeBadge('hover');
  }

  function clearSelected() {
    if (currentSelected) {
      // 同时清除选中类与残留的 hover 高亮类
      // （用户刚好 hover 在 A 上点击选 A → A 同时有 hover+selected 两个类；
      //  切换选中到 B 时若只清 selected 不清 hover → A 的 hover 残留，直到再 hover 一次 A 并 mouseout 才被 remove）
      currentSelected.classList.remove('marvis-selected-highlight', 'marvis-hover-highlight');
    }
    currentSelected = null;
    removeBadge('selected');
  }

  function handleMouseOver(e: MouseEvent) {
    if (destroyed) return;
    let target = e.target as HTMLElement | null;
    while (target && (target === doc.body || target === doc.documentElement || target.classList?.contains('marvis-tag-badge'))) {
      target = target.parentElement;
    }
    if (!target || target === currentSelected) { clearHover(); return; }
    if (currentHover) currentHover.classList.remove('marvis-hover-highlight');
    currentHover = target;
    target.classList.add('marvis-hover-highlight');
    positionBadge(target, 'hover');
    e.stopPropagation();
  }

  function handleMouseOut(e: MouseEvent) {
    if (destroyed) return;
    const target = e.target as HTMLElement;
    if (target === currentHover && target !== currentSelected) {
      target.classList.remove('marvis-hover-highlight');
    }
    // 保险：mouseout 目标元素若恰好还有 hover 高亮（即使不是 currentHover 也清）
    // 避免 Vue/Nuxt 重排导致节点引用与实际 DOM 不一致时 class 残留
    if (target !== currentSelected) {
      target.classList.remove('marvis-hover-highlight');
    }
    removeBadge('hover');
    currentHover = null;
    e.stopPropagation();
  }

  function handleScroll() {
    if (currentSelected) positionBadge(currentSelected, 'selected');
  }

  function handleClick(e: MouseEvent) {
    if (destroyed) return;
    let target = e.target as HTMLElement | null;
    while (target && (target === doc.body || target === doc.documentElement || target.classList?.contains('marvis-tag-badge'))) {
      target = target.parentElement;
    }
    if (!target) return;
    e.preventDefault();
    e.stopPropagation();

    clearSelected();
    currentSelected = target;
    target.classList.add('marvis-selected-highlight');
    positionBadge(target, 'selected');
    clearHover();

    const tag = target.tagName.toLowerCase();
    const id = target.id ? '#' + target.id : '';
    (window as any).$message?.success('已选中元素: ' + tag + id);
  }

  doc.addEventListener('mouseover', handleMouseOver, true);
  doc.addEventListener('mouseout', handleMouseOut, true);
  doc.addEventListener('click', handleClick, true);
  win.addEventListener('scroll', handleScroll, true);

  return function cleanup() {
    if (destroyed) return;
    destroyed = true;
    doc.removeEventListener('mouseover', handleMouseOver, true);
    doc.removeEventListener('mouseout', handleMouseOut, true);
    doc.removeEventListener('click', handleClick, true);
    win.removeEventListener('scroll', handleScroll, true);
    clearHover();
    clearSelected();
    doc.body.classList.remove('marvis-selecting-mode');
    style.remove();
  };
}

function toggleElementSelect() {
  elementSelectMode.value = !elementSelectMode.value;
  if (elementSelectMode.value) {
    enableElementSelection();
    createMarvisFloatButton('关闭选择元素模式', () => {
      elementSelectMode.value = false;
      disableElementSelection();
    });
  } else {
    disableElementSelection();
    removeMarvisFloatButton();
  }
}

function onIframeLoad() {
  // 初始化 lastIframePath（用于后续轮询比对 SPA 路由变化）
  try {
    const iframe = iframeRef.value;
    if (iframe?.contentWindow) {
      lastIframePath = iframe.contentWindow.location.pathname + iframe.contentWindow.location.search;
    }
  } catch { /* ignore */ }
  // 若预览模式则启动 URL 轮询（监听 Nuxt SPA 路由跳转，动态添加 tab）
  if (mode.value === 'preview') {
    startIframeUrlPolling();
  }
  // 如果处于选择模式，注入选择脚本
  if (elementSelectMode.value && mode.value === 'preview') {
    installIframeSelection();
  }
}

function installIframeSelection() {
  const iframe = iframeRef.value;
  if (!iframe) return;
  try {
    const doc = iframe.contentDocument;
    const win = iframe.contentWindow;
    if (!doc || !win) return;
    // 清理旧的
    if (globalMarvisCleanup) {
      globalMarvisCleanup();
      globalMarvisCleanup = null;
    }
    globalMarvisCleanup = installMarvisOnDoc(doc, win, true);
  } catch {
    // 跨域无法访问
    window.$message?.warning('预览页面跨域，无法选择元素。请切换到「结构编辑」模式使用选择功能');
  }
}

function installCanvasSelection() {
  const canvasHost = document.querySelector('.diy-decoration .phone-frame') as HTMLElement | null;
  if (!canvasHost) return;
  if (canvasMarvisCleanup) {
    canvasMarvisCleanup();
    canvasMarvisCleanup = null;
  }
  canvasMarvisCleanup = installMarvisOnDoc(document, window, false);
}

function enableElementSelection() {
  if (mode.value === 'preview') {
    installIframeSelection();
  } else {
    installCanvasSelection();
  }
}

function disableElementSelection() {
  if (globalMarvisCleanup) {
    globalMarvisCleanup();
    globalMarvisCleanup = null;
  }
  if (canvasMarvisCleanup) {
    canvasMarvisCleanup();
    canvasMarvisCleanup = null;
  }
  removeMarvisFloatButton();
}

// --- 画布拖拽 ---
const pageComponents = computed<any[]>({
  get: () => store.pageComponents,
  set: val => store.reorderComponents(val)
});

const rendererMap: Record<string, any> = {
  banner: BannerRenderer,
  search_box: SearchBoxRenderer,
  image_ad: ImageAdRenderer,
  text_block: TextBlockRenderer,
  rich_text: RichTextRenderer,
  video: VideoRenderer,
  divider: DividerRenderer,
  blank: BlankRenderer,
  goods_list: GoodsListRenderer,
  goods_single: GoodsSingleRenderer,
  goods_group: GoodsGroupRenderer,
  coupon: CouponRenderer,
  countdown: CountdownRenderer,
  notice_bar: NoticeBarRenderer,
  nav_group: NavGroupRenderer
};

function getRenderer(code: string) {
  return rendererMap[code] || BlankRenderer;
}

function onCanvasAdd(evt: any) {
  const list = [...pageComponents.value];
  const added = list[evt.newIndex];
  if (added && !added.component_id) {
    const lib = store.componentsLibrary.find((c: any) => c.id === added.id) || added;
    list[evt.newIndex] = {
      id: crypto.randomUUID(),
      page_id: store.currentPage?.id,
      component_id: lib.id,
      component_code: lib.code,
      component_name: lib.name,
      component_icon: lib.icon,
      config_schema: lib.config_schema || {},
      sort_order: 0,
      config: JSON.parse(JSON.stringify(lib.default_config || {})),
      is_visible: true
    };
  }
  list.forEach((c: any, i: number) => { c.sort_order = i; });
  store.reorderComponents(list);
  if (list[evt.newIndex]) {
    store.selectComponent(list[evt.newIndex].id);
  }
}

function onCanvasDragEnd() {
  const list = [...pageComponents.value];
  list.forEach((c: any, i: number) => { c.sort_order = i; });
  store.reorderComponents(list);
}

async function handleSave() {
  if (!store.activeTabId) return;
  saving.value = true;
  try {
    await store.saveComponents(store.activeTabId);
    window.$message?.success('已保存');
  } finally {
    saving.value = false;
  }
}

async function handlePublish() {
  if (!store.activeTabId) return;
  publishing.value = true;
  try {
    await store.saveComponents(store.activeTabId);
    await diyApi.publishPage(store.activeTabId);
    if (store.currentPage) {
      store.currentPage.status = 'published';
    }
    store.updateTab(store.activeTabId, { status: 'published' });
    window.$message?.success('已发布');
  } finally {
    publishing.value = false;
  }
}

// --- 新建页面 ---
const showCreate = ref(false);
const creating = ref(false);
const createForm = reactive({ name: '', slug: '', page_type: 'custom' });
const typeOptions = [
  { label: '自定义', value: 'custom' },
  { label: '分类', value: 'category' },
  { label: '商品详情', value: 'product_detail' }
];

async function handleCreate() {
  if (!createForm.name || !createForm.slug) {
    window.$message?.warning('名称和 Slug 不能为空');
    return;
  }
  creating.value = true;
  try {
    const page: any = (await diyApi.createPage({ ...createForm })).data;
    showCreate.value = false;
    createForm.name = '';
    createForm.slug = '';
    window.$message?.success('页面已创建');
    // 刷新缓存并以 tab 形式打开
    const res = await diyApi.listPages();
    allPagesCache.value = res.data?.items || [];
    const tabId = store.addTab({
      id: page.id,
      name: page.name,
      page_type: page.page_type || 'custom',
      slug: page.slug,
      status: page.status,
      components_count: page.components?.length ?? 0
    });
    store.reset();
    // 先更新 iframe src，再加载页面数据
    const newTab = store.openTabs.find(t => t.id === tabId);
    iframeSrc.value = buildPreviewUrl(newTab);
    iframeKey.value++;
    try { await store.fetchPage(tabId); } catch { /* ignore */ }
  } finally {
    creating.value = false;
  }
}

// ========== iframe SPA 路由变更检测（轮询） ==========
/** 常见 admin 内部路由 slug 黑名单：iframe 误入 admin SPA 时不应被当成自定义页面 */
const ADMIN_SLUG_BLACKLIST = new Set([
  'dashboard', 'site', 'orders', 'categories',
  'users', 'roles', 'permissions', 'login', '404', '403', '500'
]);
/** Nuxt C 端系统路由前缀（有 slug 时识别为系统页；无 slug 时忽略，不创建 tab） */
const NUXT_SYSTEM_ROUTE_PREFIXES = new Set(['category', 'products']);

/** 从 iframe pathname 推断页面信息：page_type/slug/name。
 *  iframe 加载初期路径为 /portal-preview/zh/...，Nuxt 路由初始化后变为 /zh/...，
 *  两种格式都需要支持。 */
function parseIframePath(fullPath: string): { page_type: string; slug: string; id: string; name: string } | null {
  if (!fullPath) return null;
  // 必须以 i18n 前缀 /zh 开头（Nuxt C 端所有路由都带 locale 前缀）
  // 兼容 /portal-preview/zh/... 前缀（iframe 加载初期 Vite 代理路径）
  if (!/^\/(portal-preview\/)?zh(?:\/|$|\?)/.test(fullPath)) return null;
  // 去掉 /portal-preview 前缀（如有）和 i18n 前缀 /zh
  let path = fullPath
    .replace(/^\/portal-preview(?=\/|$)/, '')
    .replace(/^\/zh(?=\/|$|\?)/, '')
    .replace(/^\//, '');
  // 去掉 query/hash
  path = path.split('?')[0].split('#')[0];

  if (!path) {
    // 空路径 = 首页
    const home = store.pinnedHome;
    if (!home) return null;
    return { page_type: 'home', slug: home.slug, id: home.id, name: home.name };
  }
  const segs = path.split('/').filter(Boolean);
  if (segs[0] === 'category' && segs[1]) {
    const slug = decodeURIComponent(segs[1]);
    return {
      page_type: 'category',
      slug,
      id: 'category',
      name: pageTypeName('category', slug)
    };
  }
  if (segs[0] === 'products' && segs[1]) {
    const slug = decodeURIComponent(segs[1]);
    return {
      page_type: 'product_detail',
      slug,
      id: 'product_detail',
      name: pageTypeName('product_detail', slug)
    };
  }
  // 系统路由前缀但无 slug（如 /zh/category, /zh/products 列表页）→ 不创建 tab
  const firstSeg = decodeURIComponent(segs[0] ?? '');
  if (!firstSeg || NUXT_SYSTEM_ROUTE_PREFIXES.has(firstSeg.toLowerCase())) {
    return null;
  }
  // admin 内部路由黑名单过滤
  if (ADMIN_SLUG_BLACKLIST.has(firstSeg.toLowerCase())) {
    return null;
  }
  // 其余：自定义页面 /:slug
  const slug = decodeURIComponent(segs.join('/'));
  const cached = allPagesCache.value.find(p => p.slug === slug && p.page_type === 'custom');
  return {
    page_type: 'custom',
    slug,
    id: cached?.id || `custom:${slug}`,
    name: cached?.name || slug
  };
}

/** 根据 iframe 当前路径动态添加 tab（若不存在）；已存在且激活则不做 */
async function handleIframeRouteChange(fullPath: string) {
  const info = parseIframePath(fullPath);
  if (!info) return;
  // 首页已固定为 pinned tab，若当前活跃则跳过
  if (info.page_type === 'home') {
    if (store.activeTabId !== info.id) {
      store.activateTab(info.id);
      store.reset();
      try { await store.fetchPage(info.id); } catch { /* ignore */ }
    }
    return;
  }
  // 系统页（category / product_detail）只按 page_type 去重：一个类型只开一个 tab，不随 URL slug 变化重复打开
  // 自定义页按 slug 去重（不同 slug = 不同页面）
  const findSlug = info.page_type === 'custom' ? info.slug : undefined;
  const existed = store.findTab(info.page_type, findSlug);
  if (existed) {
    if (store.activeTabId !== existed.id) {
      store.activateTab(existed.id);
      store.reset();
      try { await store.fetchPage(existed.id); } catch { /* ignore */ }
    }
    return;
  }
  // 新 tab：添加并加载（系统页 id 用 page_type，自定义页 id 用 UUID 或占位）
  const tabId = store.addTab({
    id: info.id,
    name: info.name,
    page_type: info.page_type,
    slug: info.slug,
    status: 'draft'
  });
  store.reset();
  try {
    await store.fetchPage(tabId);
  } catch {
    // 若 fetch 失败（页面未初始化），保持 tab 显示，内容为空，稍后用户可自行编辑保存
  }
}

let pollBadNamespaceCount = 0;

/** 启动 iframe 路径轮询：Nuxt SPA 路由切换不会触发 iframe onload，因此用轮询检测。
 *  若连续多次检测到非 Nuxt C 端命名空间（路径不以 /zh 或 /portal-preview/zh 开头），自动停止轮询并告警。
 *  注意：iframe 加载初期路径为 /portal-preview/zh/...，Nuxt 路由初始化后会变为 /zh/... */
function startIframeUrlPolling() {
  stopIframeUrlPolling();
  pollBadNamespaceCount = 0;
  urlPollTimer = window.setInterval(() => {
    const iframe = iframeRef.value;
    if (!iframe) return;
    try {
      const win = iframe.contentWindow;
      const doc = iframe.contentDocument;
      if (!win || !doc) return;
      const current = win.location.pathname + win.location.search;
      // Nuxt C 端命名空间检测：路径以 /zh 开头（Nuxt 路由初始化后）或 /portal-preview/zh 开头（加载初期）
      // 连续 10 次以上不匹配 → 判定 iframe 脱离 Nuxt C 端上下文，停止轮询
      if (!/^\/(portal-preview\/)?zh(?:\/|$|\?)/.test(win.location.pathname)) {
        pollBadNamespaceCount += 1;
        if (pollBadNamespaceCount >= 10) {
          stopIframeUrlPolling();
          window.$message?.warning(
            '预览页面脱离了站点上下文，动态页面 Tab 检测已停止。请刷新预览或检查 iframe 是否正常加载 Nuxt C 端页面（端口 3000 是否启动）。'
          );
        }
        return;
      }
      pollBadNamespaceCount = 0;
      if (current !== lastIframePath) {
        lastIframePath = current;
        handleIframeRouteChange(current);
      }
    } catch {
      // 跨域访问失败：停止轮询
      stopIframeUrlPolling();
    }
  }, 400);
}

function stopIframeUrlPolling() {
  if (urlPollTimer !== null) {
    clearInterval(urlPollTimer);
    urlPollTimer = null;
  }
}

// ========== 生命周期 ==========
onMounted(async () => {
  await Promise.all([
    loadPagesAndInitTabs(),
    store.fetchSiteConfig()
  ]);
  // 若 loadPagesAndInitTabs 内部未确保 fetchComponentsLibrary 调用，则补一次
  if (!store.componentsLibrary.length) {
    await store.fetchComponentsLibrary();
  }
});

// 模式切换：预览模式启动 URL 轮询，结构模式停止；同步元素选择脚本安装
watch(mode, newMode => {
  if (newMode === 'preview') {
    startIframeUrlPolling();
  } else {
    stopIframeUrlPolling();
  }
  if (!elementSelectMode.value) return;
  // 先清理旧安装
  if (globalMarvisCleanup) { globalMarvisCleanup(); globalMarvisCleanup = null; }
  if (canvasMarvisCleanup) { canvasMarvisCleanup(); canvasMarvisCleanup = null; }
  // 根据新模式重新安装
  if (newMode === 'preview') {
    installIframeSelection();
  } else {
    // canvas 模式 DOM 可能需要 nextTick
    setTimeout(() => installCanvasSelection(), 100);
  }
});

onUnmounted(() => {
  stopIframeUrlPolling();
  disableElementSelection();
  store.reset();
});
</script>

<style scoped>
.diy-decoration {
  height: 100%;
}

.ghost {
  opacity: 0.4;
  border: 1px dashed var(--primary-color, #18a058);
}

/* NCollapse 白色背景样式覆盖 */
.left-collapse :deep(.n-collapse-item__header),
.left-collapse :deep(.n-collapse-item__header-main),
.left-collapse :deep(.n-collapse-item__content-wrapper),
.left-collapse :deep(.n-collapse-item__content) {
  background: transparent;
}
</style>
