<template>
  <NForm label-placement="left" label-width="90px" size="small">
    <template v-for="(field, key) in properties" :key="key">
      <NFormItem :label="field.title || key">
        <!-- 自定义 widget -->
        <ProductPicker
          v-if="resolveWidget(key, field) === 'product-picker'"
          :model-value="modelValue?.[key]"
          :multiple="field.type === 'array'"
          @update:model-value="v => update(key, v)"
        />
        <CouponPicker
          v-else-if="resolveWidget(key, field) === 'coupon-picker'"
          :model-value="modelValue?.[key]"
          @update:model-value="v => update(key, v)"
        />
        <ImageUpload
          v-else-if="resolveWidget(key, field) === 'image-upload'"
          :model-value="modelValue?.[key]"
          @update:model-value="v => update(key, v)"
        />
        <RichTextEditor
          v-else-if="resolveWidget(key, field) === 'rich-editor'"
          :model-value="modelValue?.[key]"
          @update:model-value="v => update(key, v)"
        />
        <NDatePicker
          v-else-if="resolveWidget(key, field) === 'datetime'"
          type="datetime"
          clearable
          :value="parseDate(modelValue?.[key])"
          @update:value="v => update(key, v ? new Date(v).toISOString() : '')"
        />
        <NColorPicker
          v-else-if="resolveWidget(key, field) === 'color'"
          :value="modelValue?.[key]"
          @update:value="v => update(key, v)"
        />

        <!-- enum -->
        <NSelect
          v-else-if="field.enum"
          :value="modelValue?.[key]"
          :options="field.enum.map((o: string) => ({ label: o, value: o }))"
          @update:value="v => update(key, v)"
        />

        <!-- 基础类型 -->
        <NSwitch v-else-if="field.type === 'boolean'" :value="modelValue?.[key]" @update:value="v => update(key, v)" />
        <NInputNumber
          v-else-if="field.type === 'integer' || field.type === 'number'"
          :value="modelValue?.[key]"
          class="w-full"
          @update:value="v => update(key, v)"
        />
        <NInput
          v-else-if="field['ui:widget'] === 'textarea'"
          type="textarea"
          :value="modelValue?.[key]"
          :autosize="{ minRows: 3 }"
          @update:value="v => update(key, v)"
        />

        <!-- 数组类型 -->
        <template v-else-if="field.type === 'array'">
          <!-- 对象数组：动态子表单 -->
          <div v-if="field.items?.type === 'object'" class="w-full flex flex-col gap-2">
            <div
              v-for="(item, idx) in modelValue?.[key] || []"
              :key="idx"
              class="w-full rounded border border-gray-200 border-solid p-2 dark:border-gray-700"
            >
              <div class="mb-1 flex items-center justify-between">
                <span class="text-xs text-gray-400">#{{ idx + 1 }}</span>
                <NButton size="tiny" quaternary type="error" @click="removeArrayItem(key, idx)">
                  <template #icon><SvgIcon icon="mdi:close" /></template>
                </NButton>
              </div>
              <div v-for="(subField, subKey) in field.items.properties || {}" :key="subKey" class="mb-1">
                <div class="mb-0.5 text-xs text-gray-400">{{ subField.title || subKey }}</div>
                <ImageUpload
                  v-if="subKey === 'image' || subField['ui:widget'] === 'image-upload'"
                  :model-value="item[subKey]"
                  @update:model-value="v => updateArrayItem(key, idx, subKey, v)"
                />
                <NInput
                  v-else
                  size="small"
                  :value="item[subKey]"
                  @update:value="v => updateArrayItem(key, idx, subKey, v)"
                />
              </div>
            </div>
            <NButton size="small" dashed block @click="addArrayItem(key, field)">
              <template #icon><SvgIcon icon="mdi:plus" /></template>
              添加
            </NButton>
          </div>
          <!-- 字符串数组：商品多选 -->
          <ProductPicker
            v-else
            :model-value="modelValue?.[key]"
            multiple
            @update:model-value="v => update(key, v)"
          />
        </template>

        <!-- 默认文本 -->
        <NInput v-else :value="modelValue?.[key]" @update:value="v => update(key, v)" />
      </NFormItem>
    </template>
    <NEmpty v-if="!Object.keys(properties).length" description="该组件无可配置属性" />
  </NForm>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NColorPicker, NDatePicker, NEmpty, NForm, NFormItem, NInput, NInputNumber, NSelect, NSwitch } from 'naive-ui';
import ProductPicker from './widgets/ProductPicker.vue';
import CouponPicker from './widgets/CouponPicker.vue';
import ImageUpload from './widgets/ImageUpload.vue';
import RichTextEditor from './widgets/RichTextEditor.vue';

const props = defineProps<{
  schema: any;
  modelValue: Record<string, any>;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, any>): void;
}>();

const properties = computed(() => props.schema?.properties || {});

/** 解析字段控件类型 */
function resolveWidget(key: string, field: any): string | null {
  if (field['ui:widget']) return field['ui:widget'];
  // 启发式：颜色字段
  if (field.type === 'string' && /color/i.test(key)) return 'color';
  // 启发式：图片字段
  if (field.type === 'string' && /^(image|poster|avatar|logo)/i.test(key)) return 'image-upload';
  // 商品 ID 字段
  if (field.type === 'string' && /^productId$/i.test(key)) return 'product-picker';
  return null;
}

function parseDate(value: any): number | null {
  if (!value) return null;
  const t = new Date(value).getTime();
  return Number.isNaN(t) ? null : t;
}

function update(key: string | number, value: any) {
  emit('update:modelValue', { ...(props.modelValue || {}), [key]: value });
}

function addArrayItem(key: string | number, field: any) {
  const list = [...(props.modelValue?.[key] || [])];
  const empty: Record<string, any> = {};
  for (const subKey of Object.keys(field.items?.properties || {})) {
    empty[subKey] = '';
  }
  list.push(empty);
  update(key, list);
}

function removeArrayItem(key: string | number, idx: number) {
  const list = [...(props.modelValue?.[key] || [])];
  list.splice(idx, 1);
  update(key, list);
}

function updateArrayItem(key: string | number, idx: number, subKey: string | number, value: any) {
  const list = [...(props.modelValue?.[key] || [])];
  list[idx] = { ...list[idx], [subKey]: value };
  update(key, list);
}
</script>
