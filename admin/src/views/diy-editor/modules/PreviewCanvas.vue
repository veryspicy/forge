<template>
  <div class="canvas-wrapper flex flex-col overflow-hidden rounded bg-gray-100 dark:bg-true-gray-900">
    <!-- 模式切换 -->
    <div class="flex items-center justify-between border-b bg-white px-4 py-2 dark:bg-dark">
      <NButtonGroup size="small">
        <NButton :type="mode === 'canvas' ? 'primary' : 'default'" @click="mode = 'canvas'">
          组件画布
        </NButton>
        <NButton :type="mode === 'preview' ? 'primary' : 'default'" @click="mode = 'preview'">
          实时预览
        </NButton>
      </NButtonGroup>
      <NInput
        v-if="mode === 'preview'"
        v-model:value="previewUrl"
        size="small"
        placeholder="预览 URL"
        style="width: 360px"
      />
    </div>

    <!-- 组件画布模式 -->
    <div v-if="mode === 'canvas'" class="flex-1 flex justify-center overflow-y-auto p-4">
      <div class="phone-frame w-[390px] min-h-[844px] shrink-0 overflow-hidden self-start rounded-xl bg-white shadow-lg">
        <VueDraggable
          v-model="components"
          :animation="200"
          ghost-class="ghost"
          handle=".drag-handle"
          :group="{ name: 'diy', pull: true, put: true }"
          item-key="id"
          class="min-h-[844px]"
          @add="onAdd"
          @end="onDragEnd"
        >
          <DraggableComponent
            v-for="pc in components"
            :key="pc.id"
            :component="pc"
            :active="pc.id === store.activeComponentId"
            @click="store.selectComponent(pc.id)"
            @remove="store.removeComponent(pc.id)"
          >
            <component :is="getRenderer(pc.component_code)" :config="pc.config" />
          </DraggableComponent>
        </VueDraggable>
        <div
          v-if="!components.length"
          class="pointer-events-none flex h-[844px] flex-col items-center justify-center gap-2 text-gray-300"
        >
          <SvgIcon icon="mdi:gesture-tap" class="text-48px" />
          <span>从左侧组件库点击或拖入组件</span>
        </div>
      </div>
    </div>

    <!-- 实时预览模式（iframe 内嵌 Nuxt C 端） -->
    <div v-else class="flex-1 overflow-hidden">
      <iframe
        ref="iframeRef"
        :src="previewUrl"
        class="h-full w-full border-none"
        sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox"
        @load="onIframeLoad"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import { VueDraggable } from 'vue-draggable-plus';
import { NButton, NButtonGroup, NInput } from 'naive-ui';
import { useDiyStore } from '@/store/modules/diy';
import DraggableComponent from './DraggableComponent.vue';

const iframeRef = ref<HTMLIFrameElement | null>(null);
import BannerRenderer from './renderers/BannerRenderer.vue';
import SearchBoxRenderer from './renderers/SearchBoxRenderer.vue';
import ImageAdRenderer from './renderers/ImageAdRenderer.vue';
import TextBlockRenderer from './renderers/TextBlockRenderer.vue';
import RichTextRenderer from './renderers/RichTextRenderer.vue';
import VideoRenderer from './renderers/VideoRenderer.vue';
import DividerRenderer from './renderers/DividerRenderer.vue';
import BlankRenderer from './renderers/BlankRenderer.vue';
import GoodsListRenderer from './renderers/GoodsListRenderer.vue';
import GoodsSingleRenderer from './renderers/GoodsSingleRenderer.vue';
import GoodsGroupRenderer from './renderers/GoodsGroupRenderer.vue';
import CouponRenderer from './renderers/CouponRenderer.vue';
import CountdownRenderer from './renderers/CountdownRenderer.vue';
import NoticeBarRenderer from './renderers/NoticeBarRenderer.vue';
import NavGroupRenderer from './renderers/NavGroupRenderer.vue';

const store = useDiyStore();

const mode = ref<'canvas' | 'preview'>('canvas');

const defaultPreviewUrl = computed(() => {
  const base = '/portal-preview/zh';
  const page = store.currentPage;
  if (!page) return `${base}`;
  const slug = page.slug || page.page_type || '';
  if (page.page_type === 'home' || !page.page_type) {
    return `${base}?preview=true`;
  }
  if (page.page_type === 'category') {
    return `${base}/category/${slug}?preview=true`;
  }
  if (page.page_type === 'product_detail') {
    return `${base}/product/${slug}?preview=true`;
  }
  return `${base}/${slug}?preview=true`;
});

const previewUrl = ref(defaultPreviewUrl.value);

watch(() => store.currentPage, () => {
  previewUrl.value = defaultPreviewUrl.value;
}, { immediate: true });

const components = computed<any[]>({
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

function onAdd(evt: any) {
  const list = [...components.value];
  const added = list[evt.newIndex];
  if (added && !added.component_id) {
    const lib = store.componentsLibrary.find(c => c.id === added.id) || added;
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
  list.forEach((c, i) => {
    c.sort_order = i;
  });
  store.reorderComponents(list);
  if (list[evt.newIndex]) {
    store.selectComponent(list[evt.newIndex].id);
  }
}

function onDragEnd() {
  const list = [...components.value];
  list.forEach((c, i) => {
    c.sort_order = i;
  });
  store.reorderComponents(list);
}

/** iframe load 时注入导航守卫：与 index.vue 同源，防止 logo/链接跳出代理命名空间到 admin 首页 */
function onIframeLoad() {
  const iframe = iframeRef.value;
  if (!iframe) return;
  let win: Window | null = null;
  let doc: Document | null = null;
  try { win = iframe.contentWindow; doc = iframe.contentDocument; if (!win || !doc) return; }
  catch { return; }

  try {
    doc.addEventListener('click', (e) => {
      const a = (e.target as HTMLElement | null)?.closest?.('a') as HTMLAnchorElement | null;
      if (!a) return;
      const tgt = a.getAttribute('target') || '';
      if (tgt && tgt !== '_self' && tgt !== '_blank') a.setAttribute('target', '_self');
      let href = a.getAttribute('href') || '';
      if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith('mailto:')) {
        if (href.startsWith('/') && !href.startsWith('/portal-preview/')) {
          if (href === '/' || href === '') href = '/portal-preview/zh';
          else if (href.startsWith('/zh/') || href === '/zh' || href.startsWith('/zh?')) href = '/portal-preview' + href;
          else href = '/portal-preview/zh' + (href.startsWith('/') ? href : '/' + href);
          try { a.setAttribute('href', href); } catch { /* noop */ }
        }
      }
    }, true);
  } catch { /* noop */ }

  try {
    // eslint-disable-next-line no-underscore-dangle
    if ((win as any).__diyGuardInstalled) return;
    // eslint-disable-next-line no-underscore-dangle
    (win as any).__diyGuardInstalled = true;
    const rewrite = (raw: string): string | null => {
      if (!raw) return null;
      if (/^https?:\/\//.test(raw)) {
        try {
          const u = new URL(raw);
          if (u.hostname !== 'localhost' && u.hostname !== '127.0.0.1') return null;
          raw = u.pathname + u.search + u.hash;
        } catch { return null; }
      }
      if (raw.startsWith('/') && !raw.startsWith('/portal-preview/')) {
        if (raw === '/' || raw === '') return '/portal-preview/zh';
        if (raw.startsWith('/zh/') || raw === '/zh' || raw.startsWith('/zh?')) return '/portal-preview' + raw;
        if (raw.startsWith('/en/') || raw === '/en' || raw.startsWith('/en?')) return '/portal-preview' + raw;
        if (raw.startsWith('/ar/') || raw === '/ar' || raw.startsWith('/ar?')) return '/portal-preview' + raw;
        return '/portal-preview/zh' + (raw.startsWith('/') ? raw : '/' + raw);
      }
      return null;
    };
    // patch history.pushState/replaceState：SPA 导航补 preview=true
    try {
      const ensurePreview = (url: string | URL | null | undefined): any => {
        if (!url) return [url];
        const raw = String(url);
        let path = raw;
        if (/^https?:\/\//.test(raw)) {
          try {
            const u = new URL(raw);
            if (u.hostname !== 'localhost' && u.hostname !== '127.0.0.1') return [url];
            path = u.pathname + u.search + u.hash;
          } catch { return [url]; }
        }
        if (!/[?&]preview=/.test(path)) {
          const sep = path.includes('?') ? '&' : '?';
          path = path + sep + 'preview=true';
          if (/^https?:\/\//.test(raw)) {
            try {
              const u = new URL(raw);
              u.searchParams.set('preview', 'true');
              return [u.toString()];
            } catch { /* fallthrough */ }
          }
          return [path];
        }
        return [url];
      };
      const hs = win.history;
      const origPush = hs.pushState.bind(hs);
      // eslint-disable-next-line no-underscore-dangle
      const _pushState = origPush;
      (hs as any).pushState = function (...args: any[]) {
        const fixed = ensurePreview(args[2]);
        args[2] = fixed[0];
        return _pushState(...args);
      };
      const origReplace = hs.replaceState.bind(hs);
      // eslint-disable-next-line no-underscore-dangle
      const _replaceState = origReplace;
      (hs as any).replaceState = function (...args: any[]) {
        const fixed = ensurePreview(args[2]);
        args[2] = fixed[0];
        return _replaceState(...args);
      };
    } catch { /* noop */ }
    try {
      // eslint-disable-next-line no-underscore-dangle
      const _assign = win.location.assign.bind(win.location);
      (win.location as any).assign = function (url: string | URL) {
        const fixed = rewrite(String(url));
        if (fixed) return _assign(fixed);
        return _assign(url);
      };
      // eslint-disable-next-line no-underscore-dangle
      const _replace = win.location.replace.bind(win.location);
      (win.location as any).replace = function (url: string | URL) {
        const fixed = rewrite(String(url));
        if (fixed) return _replace(fixed);
        return _replace(url);
      };
    } catch { /* readonly in some browsers */ }
  } catch { /* noop */ }
}

onBeforeUnmount(() => {
  // cleanup (noop)
});
</script>

<style scoped>
.ghost {
  opacity: 0.4;
  border: 1px dashed var(--primary-color, #18a058);
}
</style>
