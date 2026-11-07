<template>
  <div
    class="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-stone-950"
    :lang="htmlLangDir.lang"
    :dir="htmlLangDir.dir"
  >
    <div class="text-center px-4">
      <h1 class="text-8xl font-bold text-neutral-200 mb-4">{{ error.statusCode }}</h1>
      <p class="text-xl text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 mb-8">
        {{ statusText }}
      </p>
      <NuxtLink
        :to="localePath('/')"
        class="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
      >
        {{ $t('common.backHome') }}
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NuxtError } from '#app';

const props = defineProps<{
  error: NuxtError;
}>();

const localePath = useLocalePath();
const { t, te } = useI18n();

// 错误页也要输出 html lang/dir（此前 AR 下 404 页仍是 LTR，整页镜像失效）。
// dir 判定复用 useDirection，与 app.vue 保持同一单一来源；unhead 不收 ComputedRef，用 getter 形式。
const { htmlLangDir } = useDirection();

useHead(() => ({
  htmlAttrs: { ...htmlLangDir.value },
}));

const statusText = computed(() => {
  if (props.error.statusCode === 404) {
    return te('errors.NOT_FOUND') ? t('errors.NOT_FOUND') : '页面不存在';
  }
  if (props.error.statusCode && props.error.statusCode >= 500) {
    return te('errors.SERVER_ERROR') ? t('errors.SERVER_ERROR') : '服务暂时不可用';
  }
  return props.error.message || (te('errors.UNKNOWN_ERROR') ? t('errors.UNKNOWN_ERROR') : '操作失败');
});
</script>
