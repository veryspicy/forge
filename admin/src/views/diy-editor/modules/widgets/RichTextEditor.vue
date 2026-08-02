<template>
  <div class="rich-text-editor w-full rounded border border-gray-200 border-solid dark:border-gray-700">
    <div class="flex gap-1 border-b border-gray-200 border-solid p-1 dark:border-gray-700">
      <NButton size="tiny" quaternary title="加粗" @click="exec('bold')"><SvgIcon icon="mdi:format-bold" /></NButton>
      <NButton size="tiny" quaternary title="斜体" @click="exec('italic')"><SvgIcon icon="mdi:format-italic" /></NButton>
      <NButton size="tiny" quaternary title="下划线" @click="exec('underline')"><SvgIcon icon="mdi:format-underline" /></NButton>
      <NButton size="tiny" quaternary title="无序列表" @click="exec('insertUnorderedList')"><SvgIcon icon="mdi:format-list-bulleted" /></NButton>
      <NButton size="tiny" quaternary title="清除格式" @click="exec('removeFormat')"><SvgIcon icon="mdi:format-clear" /></NButton>
    </div>
    <div
      ref="editorRef"
      class="min-h-[120px] p-2 text-sm outline-none"
      contenteditable="true"
      @input="onInput"
      @blur="onInput"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { NButton } from 'naive-ui';

const props = defineProps<{
  modelValue?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const editorRef = ref<HTMLElement | null>(null);

function syncContent() {
  if (editorRef.value && editorRef.value.innerHTML !== (props.modelValue || '')) {
    editorRef.value.innerHTML = props.modelValue || '';
  }
}

function exec(command: string) {
  document.execCommand(command, false);
  onInput();
}

function onInput() {
  emit('update:modelValue', editorRef.value?.innerHTML || '');
}

onMounted(syncContent);
watch(() => props.modelValue, syncContent);
</script>
