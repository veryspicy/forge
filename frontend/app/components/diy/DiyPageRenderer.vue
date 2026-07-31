<template>
  <div class="diy-page">
    <!-- Loading 骨架屏 -->
    <div v-if="pending" class="mx-auto max-w-6xl space-y-4 px-4 py-8">
      <div v-for="n in 4" :key="n" class="skeleton h-32 w-full rounded-xl" />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="py-16 text-center">
      <p class="mb-4 text-gray-500">{{ $t('common.loadFailed') || 'Failed to load page' }}</p>
      <button
        class="rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white transition hover:bg-primary-700"
        @click="$emit('retry')"
      >
        {{ $t('common.retry') || 'Retry' }}
      </button>
    </div>

    <!-- 正常渲染 -->
    <template v-else-if="visibleComponents.length">
      <component
        :is="componentMap[pc.component_code]"
        v-for="pc in visibleComponents"
        :key="pc.id"
        :config="pc.config || {}"
        :data="pc.data || {}"
      />
    </template>

    <!-- 空状态 -->
    <div v-else class="py-16 text-center text-gray-400">
      {{ $t('common.empty') || 'No content' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, resolveComponent } from 'vue'

const props = withDefaults(
  defineProps<{
    components: any[]
    pending?: boolean
    error?: boolean
  }>(),
  { pending: false, error: false },
)

defineEmits<{ (e: 'retry'): void }>()

const visibleComponents = computed(() =>
  (props.components || []).filter((pc) => pc.is_visible !== false),
)

const componentMap: Record<string, any> = {
  banner: resolveComponent('DiyBanner'),
  search_box: resolveComponent('DiySearchBox'),
  image_ad: resolveComponent('DiyImageAd'),
  text_block: resolveComponent('DiyTextBlock'),
  rich_text: resolveComponent('DiyRichText'),
  video: resolveComponent('DiyVideo'),
  divider: resolveComponent('DiyDivider'),
  blank: resolveComponent('DiyBlank'),
  goods_list: resolveComponent('DiyGoodsList'),
  goods_single: resolveComponent('DiyGoodsSingle'),
  goods_group: resolveComponent('DiyGoodsGroup'),
  coupon: resolveComponent('DiyCoupon'),
  countdown: resolveComponent('DiyCountdown'),
  notice_bar: resolveComponent('DiyNoticeBar'),
  nav_group: resolveComponent('DiyNavGroup'),
}
</script>
