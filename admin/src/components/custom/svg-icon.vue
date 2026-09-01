<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useAttrs, watch } from 'vue';
import { Icon, iconLoaded, loadIcon } from '@iconify/vue';

defineOptions({ name: 'SvgIcon', inheritAttrs: false });

/**
 * Props
 *
 * - Support iconify and local svg icon
 * - If icon and localIcon are passed at the same time, localIcon will be rendered first
 */
interface Props {
  /** Iconify icon name */
  icon?: string;
  /** Local svg icon name */
  localIcon?: string;
}

const props = defineProps<Props>();

const attrs = useAttrs();

const bindAttrs = computed<{ class: string; style: string }>(() => ({
  class: (attrs.class as string) || '',
  style: (attrs.style as string) || ''
}));

const symbolId = computed(() => {
  const { VITE_ICON_LOCAL_PREFIX: prefix } = import.meta.env;

  const defaultLocalIcon = 'no-icon';

  const icon = props.localIcon || defaultLocalIcon;

  return `#${prefix}-${icon}`;
});

/** If localIcon is passed, render localIcon first */
const renderLocalIcon = computed(() => props.localIcon || !props.icon);

/**
 * Iconify remote icon resolution guard (fallback for setFetch not being installed
 * in edge cases such as lazy plugin loading).
 *
 * Without this, Icon stays in a pending-render state while @iconify/vue waits on
 * Promise<fetch> against iconify.design → combined with <Transition mode="out-in">,
 * the parent slot never commits its final render. Chrome interprets this as
 * "Page Not Responding" after ~8s of the form inputs not mounting.
 *
 * Guard logic:
 *   1. If icon is already in the iconify local cache → OK, render Icon immediately.
 *   2. Otherwise race loadIcon() against a 1500ms timeout.
 *   3. Winner takes all:
 *      - loadIcon resolves → show Icon
 *      - timeout wins → set remoteUnavailable=true → stop waiting, fall through to an
 *        empty inline SVG placeholder. The page can now finish mounting.
 */
const REMOTE_TIMEOUT_MS = 1500;
const remoteUnavailable = ref(false);
let remoteTimer: number | undefined;
let abortLoad: (() => void) | undefined;

function clearRemoteTimer() {
  if (remoteTimer !== undefined) {
    window.clearTimeout(remoteTimer);
    remoteTimer = undefined;
  }
  if (abortLoad) {
    abortLoad = undefined;
  }
}

async function resolveRemoteIcon(name: string) {
  clearRemoteTimer();
  remoteUnavailable.value = false;

  if (iconLoaded(name)) {
    return;
  }

  const timeout = new Promise<void>(resolve => {
    remoteTimer = window.setTimeout(() => {
      remoteUnavailable.value = true;
      resolve();
    }, REMOTE_TIMEOUT_MS);
  });

  let cancelled = false;
  abortLoad = () => {
    cancelled = true;
  };

  try {
    await Promise.race([
      loadIcon(name).then(() => {
        if (!cancelled) remoteUnavailable.value = false;
      }),
      timeout
    ]);
  } catch {
    remoteUnavailable.value = true;
  } finally {
    clearRemoteTimer();
  }
}

watch(
  () => props.icon,
  val => {
    if (!val || renderLocalIcon.value) {
      clearRemoteTimer();
      remoteUnavailable.value = false;
      return;
    }
    resolveRemoteIcon(val);
  },
  { immediate: true, flush: 'post' }
);

onBeforeUnmount(() => {
  clearRemoteTimer();
});
</script>

<template>
  <template v-if="renderLocalIcon">
    <svg aria-hidden="true" width="1em" height="1em" v-bind="bindAttrs">
      <use :xlink:href="symbolId" fill="currentColor" />
    </svg>
  </template>
  <template v-else-if="remoteUnavailable">
    <!-- Remote icon timed out: render an invisible 1em placeholder so layout does
         not break and the parent Transition can commit its final DOM. -->
    <svg
      aria-hidden="true"
      width="1em"
      height="1em"
      viewBox="0 0 24 24"
      v-bind="bindAttrs"
    />
  </template>
  <template v-else>
    <Icon v-if="icon" :icon="icon" v-bind="bindAttrs" />
  </template>
</template>

<style scoped></style>
