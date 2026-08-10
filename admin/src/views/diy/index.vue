<template>
  <div class="diy-decoration flex h-full gap-0" style="min-height: calc(100vh - 180px)">
    <!-- 左侧面板：页面列表 + 站点配置 + 组件库（统一折叠） -->
    <div v-if="leftPanelVisible" class="flex w-[280px] shrink-0 flex-col overflow-hidden rounded bg-white shadow-sm dark:bg-dark">
      <NCollapse :default-expanded-names="['pages', 'components']" class="left-collapse flex-1">
        <!-- 页面 -->
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
              v-for="page in pages"
              :key="page.id"
              class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors"
              :class="selectedPageId === page.id
                ? 'bg-primary/10 text-primary font-medium'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800'"
              @click="selectPage(page)"
            >
              <SvgIcon :icon="pageIcon(page.page_type)" class="text-16px shrink-0" />
              <span class="truncate">{{ page.name }}</span>
              <NTag :bordered="false" size="tiny" :type="page.status === 'published' ? 'success' : 'default'" class="ml-auto shrink-0">
                {{ page.status === 'published' ? '已发布' : '草稿' }}
              </NTag>
            </div>
          </div>
          <NEmpty v-if="!pages.length" description="暂无页面" class="mt-2" />
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
              ref="iframeRef"
              :src="previewUrl"
              class="h-full w-full border-none"
              sandbox="allow-scripts allow-same-origin"
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
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
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

// --- 页面列表 ---
const pages = ref<any[]>([]);
const selectedPageId = ref<string | null>(null);
const mode = ref<'preview' | 'canvas'>('preview');
const device = ref<'desktop' | 'tablet' | 'mobile'>('desktop');
const saving = ref(false);
const publishing = ref(false);
const leftPanelVisible = ref(true);
const panelVisible = ref(false);
const iframeRef = ref<HTMLIFrameElement | null>(null);
const elementSelectMode = ref(false);

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

const previewUrl = computed(() => {
  const page = store.currentPage;
  if (!page) return 'http://localhost:3000/?preview=true';
  if (page.page_type === 'home') return 'http://localhost:3000/?preview=true';
  if (page.page_type === 'category') return `http://localhost:3000/category/${page.slug || 'all'}?preview=true`;
  if (page.page_type === 'product_detail') return `http://localhost:3000/products/${page.slug || 'demo'}?preview=true`;
  return `http://localhost:3000/${page.slug}?preview=true`;
});

async function loadPages() {
  try {
    const res = await diyApi.listPages();
    // diyApi.listPages 内部已将 system+custom 合并，返回 { data: { items, total } }
    pages.value = res.data?.items || [];
  } catch {
    pages.value = [];
  }
}

async function selectPage(page: any) {
  if (selectedPageId.value === page.id) return;
  selectedPageId.value = page.id;
  store.reset();
  await Promise.all([
    store.fetchComponentsLibrary(),
    store.fetchPage(page.id)
  ]);
}

function switchMode(m: 'preview' | 'canvas') {
  mode.value = m;
}

function openInBrowser() {
  window.open(previewUrl.value, '_blank');
}

function toggleElementSelect() {
  elementSelectMode.value = !elementSelectMode.value;
  if (elementSelectMode.value) {
    enableElementSelection();
  } else {
    disableElementSelection();
  }
}

function enableElementSelection() {
  const iframe = iframeRef.value;
  if (!iframe?.contentDocument) return;

  const style = iframe.contentDocument.createElement('style');
  style.id = 'marvis-element-select';
  style.textContent = '.marvis-hover-highlight{outline:2px solid #18a058!important;outline-offset:-2px}';
  iframe.contentDocument.head.appendChild(style);

  const handleMouseOver = (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target === iframe.contentDocument?.body || target === iframe.contentDocument?.documentElement) return;
    target.classList.add('marvis-hover-highlight');
    e.stopPropagation();
  };
  const handleMouseOut = (e: MouseEvent) => {
    (e.target as HTMLElement).classList.remove('marvis-hover-highlight');
    e.stopPropagation();
  };
  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const target = e.target as HTMLElement;
    let selector = target.tagName.toLowerCase();
    if (target.id) selector += '#' + target.id;
    else if (target.className && typeof target.className === 'string') {
      const cls = target.className.split(' ').filter((c: string) => c && c !== 'marvis-hover-highlight').join('.');
      if (cls) selector += '.' + cls;
    }
    (window as any).$message?.info('已选中元素: ' + selector);
    elementSelectMode.value = false;
    disableElementSelection();
  };

  iframe.contentDocument.addEventListener('mouseover', handleMouseOver, true);
  iframe.contentDocument.addEventListener('mouseout', handleMouseOut, true);
  iframe.contentDocument.addEventListener('click', handleClick, true);
  (iframe as any)._marvisHandlers = { handleMouseOver, handleMouseOut, handleClick };
}

function disableElementSelection() {
  const iframe = iframeRef.value;
  if (!iframe?.contentDocument) {
    elementSelectMode.value = false;
    return;
  }

  const style = iframe.contentDocument.getElementById('marvis-element-select');
  style?.remove();

  const handlers = (iframe as any)._marvisHandlers;
  if (handlers) {
    iframe.contentDocument.removeEventListener('mouseover', handlers.handleMouseOver, true);
    iframe.contentDocument.removeEventListener('mouseout', handlers.handleMouseOut, true);
    iframe.contentDocument.removeEventListener('click', handlers.handleClick, true);
    delete (iframe as any)._marvisHandlers;
  }
  iframe.contentDocument.querySelectorAll('.marvis-hover-highlight').forEach((el: Element) => el.classList.remove('marvis-hover-highlight'));
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
  if (!selectedPageId.value) return;
  saving.value = true;
  try {
    await store.saveComponents(selectedPageId.value);
    window.$message?.success('已保存');
  } finally {
    saving.value = false;
  }
}

async function handlePublish() {
  if (!selectedPageId.value) return;
  publishing.value = true;
  try {
    await store.saveComponents(selectedPageId.value);
    await diyApi.publishPage(selectedPageId.value);
    if (store.currentPage) {
      store.currentPage.status = 'published';
    }
    const page = pages.value.find(p => p.id === selectedPageId.value);
    if (page) page.status = 'published';
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
    const res = await diyApi.createPage({ ...createForm });
    showCreate.value = false;
    createForm.name = '';
    createForm.slug = '';
    window.$message?.success('页面已创建');
    await loadPages();
    await selectPage(res.data);
  } finally {
    creating.value = false;
  }
}

onMounted(async () => {
  await loadPages();
  await Promise.all([
    store.fetchComponentsLibrary(),
    store.fetchSiteConfig()
  ]);
  // 默认选中首页
  if (pages.value.length) {
    await selectPage(pages.value[0]);
  }
});

onUnmounted(() => {
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
