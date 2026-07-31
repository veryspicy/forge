<template>
  <div class="canvas-wrapper flex justify-center overflow-y-auto rounded bg-gray-100 p-4 dark:bg-true-gray-900">
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
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { VueDraggable } from 'vue-draggable-plus';
import { useDiyStore } from '@/store/modules/diy';
import DraggableComponent from './DraggableComponent.vue';
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

/** 从组件库拖入画布后：修正 sort_order 并选中新组件 */
function onAdd(evt: any) {
  const list = [...components.value];
  const added = list[evt.newIndex];
  if (added && !added.component_id) {
    // 兼容处理：若插入的是组件库原始定义对象，转换为 PageComponent 实例
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
</script>

<style scoped>
.ghost {
  opacity: 0.4;
  border: 1px dashed var(--primary-color, #18a058);
}
</style>
