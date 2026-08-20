<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold m-0">{{ isEdit ? t('common.edit') + ' ' + t('common.product') : t('common.new') + ' ' + t('common.product') }}</h2>
      <NButton @click="$router.push('/products')">{{ $t('common.backToList') }}</NButton>
    </div>

    <div v-if="error" class="bg-red-50 text-red-600 p-3 rounded text-sm">{{ error }}</div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Basic Info -->
      <NCard :title="$t('common.basicInfo')" size="small" class="md:col-span-2">
        <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.sku')" required><NInput v-model:value="form.sku" /></NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.name')" required><NInput v-model:value="form.name" /></NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.productsDetail.slug')"><NInput v-model:value="form.slug" /></NFormItem>
          </NGi>
          <NGi span="1">
            <NFormItem :label="$t('page.products.category')">
              <NSelect v-model:value="form.category" :options="categoryOptions" />
            </NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('common.description')"><NInput v-model:value="form.description" type="textarea" :rows="3" /></NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Translations -->
      <NCard title="多语言内容" size="small" class="md:col-span-2">
        <NFormItem label="语言">
          <NSelect
            :value="currentLang"
            :options="langOptions"
            style="width:200px"
            @update:value="switchLang"
          />
        </NFormItem>
        <NGrid :cols="2" :x-gap="16" responsive="screen">
          <NGi span="2">
            <NFormItem label="名称翻译">
              <NInput v-model:value="translationName" @update:value="syncLang('name')" />
            </NFormItem>
          </NGi>
          <NGi span="2">
            <NFormItem label="描述翻译">
              <NInput v-model:value="translationDesc" type="textarea" :rows="3" @update:value="syncLang('desc')" />
            </NFormItem>
          </NGi>
          <NGi span="2">
            <NFormItem label="AI 描述翻译">
              <NInput v-model:value="translationAi" type="textarea" :rows="3" @update:value="syncLang('ai')" />
            </NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Pricing -->
      <NCard :title="$t('page.pricing.title')" size="small">
        <NFormItem :label="$t('page.products.price')"><NInputNumber v-model:value="form.price" :min="0" :step="0.01" style="width:100%" /></NFormItem>
        <NFormItem :label="$t('common.cost')"><NInputNumber v-model:value="form.cost" :min="0" :step="0.01" style="width:100%" /></NFormItem>
      </NCard>

      <!-- Inventory -->
      <NCard :title="$t('common.inventory')" size="small">
        <NFormItem :label="$t('page.productsDetail.inventory')"><NInputNumber v-model:value="form.inventory" :min="0" style="width:100%" /></NFormItem>
        <NFormItem :label="$t('page.productsDetail.aiGenerated')">
          <NSwitch v-model:value="form.is_ai_generated" />
        </NFormItem>
      </NCard>

      <!-- Tags & Regions -->
      <NCard :title="$t('common.tagsRegions')" size="small" class="md:col-span-2">
        <NGrid :cols="2" :x-gap="16" responsive="screen">
          <NGi span="1 m:2">
            <NFormItem :label="$t('page.productsDetail.tagsComma')"><NInput v-model:value="tagsString" @update:value="updateTags" /></NFormItem>
          </NGi>
          <NGi span="1 m:2">
            <NFormItem :label="$t('page.productsDetail.regionsComma')"><NInput v-model:value="regionsString" @update:value="updateRegions" /></NFormItem>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Images -->
      <NCard :title="$t('common.productImages')" size="small" class="md:col-span-2">
        <div v-if="images.length" class="flex flex-wrap gap-3 mb-4">
          <div v-for="(img, idx) in images" :key="img.key || idx" class="relative w-[100px] h-[100px] rounded-md overflow-hidden border border-[var(--n-border-color)]">
            <NImage :src="img.url" width="100" height="100" style="object-fit:cover" />
            <NButton
              class="absolute top-0.5 right-0.5"
              size="tiny" circle type="error"
              @click="removeImage(idx)"
            >&times;</NButton>
          </div>
        </div>
        <NUpload
          :multiple="true"
          accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml,image/bmp"
          :show-file-list="false"
          :custom-request="handleUpload"
          :disabled="uploading"
        >
          <NButton :loading="uploading">{{ $t('common.uploadImages') }}</NButton>
        </NUpload>
      </NCard>

      <!-- Variants (edit only) -->
      <NCard v-if="isEdit" title="变体管理" size="small" class="md:col-span-2">
        <div class="mb-3">
          <NButton size="small" type="primary" @click="openVariantModal()">新增变体</NButton>
        </div>
        <NTable v-if="variants.length" size="small" :bordered="true" :single-line="false">
          <thead>
            <tr>
              <th>名称</th><th>SKU</th><th>属性</th><th>价格</th><th>成本</th><th>库存</th><th>状态</th><th>默认</th><th style="width:170px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in variants" :key="v.id">
              <td>{{ v.name }}</td>
              <td>{{ v.sku }}</td>
              <td class="text-xs opacity-70">{{ JSON.stringify(v.attributes || {}) }}</td>
              <td>{{ v.price }}</td>
              <td>{{ v.cost }}</td>
              <td>{{ v.inventory }}</td>
              <td>{{ v.status }}</td>
              <td>{{ v.is_default ? '✓' : '' }}</td>
              <td>
                <NSpace size="small">
                  <NButton size="tiny" @click="openVariantModal(v)">编辑</NButton>
                  <NButton size="tiny" type="error" @click="deleteVariant(v.id)">删除</NButton>
                </NSpace>
              </td>
            </tr>
          </tbody>
        </NTable>
        <NEmpty v-else description="暂无变体" size="small" class="py-6" />
      </NCard>

      <!-- Variant Modal -->
      <NModal
        v-model:show="variantModal.show"
        :title="variantModal.id ? '编辑变体' : '新增变体'"
        preset="card"
        style="width: 560px"
      >
        <NForm label-placement="top">
          <NFormItem label="SKU" required><NInput v-model:value="variantForm.sku" /></NFormItem>
          <NFormItem label="名称" required><NInput v-model:value="variantForm.name" /></NFormItem>
          <NFormItem label="属性 (JSON)">
            <NInput v-model:value="variantForm.attributesText" placeholder='{"color":"blue","size":"M"}' />
          </NFormItem>
          <NGrid :cols="3" :x-gap="12" responsive="screen">
            <NGi>
              <NFormItem label="价格"><NInputNumber v-model:value="variantForm.price" :min="0" :step="0.01" style="width:100%" /></NFormItem>
            </NGi>
            <NGi>
              <NFormItem label="成本"><NInputNumber v-model:value="variantForm.cost" :min="0" :step="0.01" style="width:100%" /></NFormItem>
            </NGi>
            <NGi>
              <NFormItem label="库存"><NInputNumber v-model:value="variantForm.inventory" :min="0" style="width:100%" /></NFormItem>
            </NGi>
          </NGrid>
          <NGrid :cols="2" :x-gap="12" responsive="screen">
            <NGi>
              <NFormItem label="状态">
                <NSelect v-model:value="variantForm.status" :options="statusOptions" />
              </NFormItem>
            </NGi>
            <NGi>
              <NFormItem label="设为默认变体"><NSwitch v-model:value="variantForm.is_default" /></NFormItem>
            </NGi>
          </NGrid>
        </NForm>
        <template #footer>
          <NSpace justify="end">
            <NButton @click="variantModal.show = false">取消</NButton>
            <NButton type="primary" :loading="variantSaving" @click="saveVariant">保存</NButton>
          </NSpace>
        </template>
      </NModal>

      <!-- Danger Zone (edit only) -->
      <NCard v-if="isEdit" :title="$t('common.dangerZone')" size="small" class="md:col-span-2">
        <NSpace>
          <NSelect
            v-model:value="statusChange"
            :options="statusOptions"
            :placeholder="$t('page.productsDetail.changeStatus')"
            style="width:140px"
            clearable
          />
          <NButton v-if="statusChange" @click="changeStatus" type="warning">{{ $t('page.productsDetail.updateStatus') }}</NButton>
        </NSpace>
      </NCard>
    </div>

    <div class="flex justify-end">
      <NButton type="primary" :loading="saving" @click="save">{{ $t('common.save') }}</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton, NCard, NEmpty, NForm, NFormItem, NGi, NGrid, NImage, NInput, NInputNumber,
  NModal, NSelect, NSpace, NSwitch, NTable, NUpload,
} from 'naive-ui';
import { useI18n } from 'vue-i18n';
import { get, post, patch, del } from '@/service/api/helper';

const route = useRoute();
const { t } = useI18n();
const router = useRouter();
const isEdit = computed(() => !!route.params.id);

const error = ref('');
const saving = ref(false);
const uploading = ref(false);

const tagsString = ref('');
const regionsString = ref('');
const statusChange = ref<string | null>(null);

const images = ref<{ key: string; url: string; alt?: string }[]>([]);
const pendingFiles = ref<File[]>([]);

const variants = ref<any[]>([]);
const variantModal = ref({ show: false, id: '' });
const variantSaving = ref(false);
const variantForm = ref({
  sku: '', name: '', attributesText: '',
  price: 0, cost: 0, inventory: 0, status: 'active', is_default: false,
});

const form = ref({
  sku: '', name: '', slug: '', category: 'FOOD', description: '',
  price: 0, cost: 0, inventory: 0, is_ai_generated: false,
  tags: [] as string[], region_availability: [] as string[],
  name_translations: {} as Record<string, string>,
  description_translations: {} as Record<string, string>,
  ai_description_translations: {} as Record<string, string>,
});

const langOptions = [
  { label: 'English (en)', value: 'en' },
  { label: 'العربية (ar)', value: 'ar' },
  { label: '简体中文 (zh-cn)', value: 'zh-cn' },
  { label: 'Français (fr)', value: 'fr' },
  { label: 'Español (es)', value: 'es' },
  { label: 'Deutsch (de)', value: 'de' },
];

const currentLang = ref('en');
const translationName = ref('');
const translationDesc = ref('');
const translationAi = ref('');

function loadLang(lang: string) {
  translationName.value = form.value.name_translations?.[lang] || '';
  translationDesc.value = form.value.description_translations?.[lang] || '';
  translationAi.value = form.value.ai_description_translations?.[lang] || '';
}

function switchLang(lang: string) {
  syncLang('name'); syncLang('desc'); syncLang('ai');
  currentLang.value = lang;
  loadLang(lang);
}

function syncLang(kind: 'name' | 'desc' | 'ai') {
  const key = kind === 'name' ? 'name_translations'
    : kind === 'desc' ? 'description_translations'
    : 'ai_description_translations';
  form.value[key][currentLang.value] =
    kind === 'name' ? translationName.value
    : kind === 'desc' ? translationDesc.value
    : translationAi.value;
}

const categoryOptions = [
  { label: 'Food', value: 'FOOD' }, { label: 'Toy', value: 'TOY' },
  { label: 'Health', value: 'HEALTH' }, { label: 'Accessory', value: 'ACCESSORY' },
  { label: 'Service', value: 'SERVICE' },
];

const statusOptions = [
  { label: 'Active', value: 'active' }, { label: 'Draft', value: 'draft' }, { label: 'Inactive', value: 'inactive' },
];

function updateTags() { form.value.tags = tagsString.value.split(',').map(s => s.trim()).filter(Boolean); }
function updateRegions() { form.value.region_availability = regionsString.value.split(',').map(s => s.trim()).filter(Boolean); }

onMounted(async () => {
  if (!isEdit.value) return;
  try {
    const res = await get(`/api/admin/v1/products/${route.params.id}`);
    const p = res.data?.data ?? res.data;
    form.value = {
      sku: p.sku || '', name: p.name || '', slug: p.slug || '',
      category: p.category || 'FOOD', description: p.description || '',
      price: p.price || 0, cost: p.cost || 0, inventory: p.inventory || 0,
      is_ai_generated: p.is_ai_generated || false,
      tags: p.tags || [], region_availability: p.region_availability || [],
      name_translations: p.name_translations || {},
      description_translations: p.description_translations || {},
      ai_description_translations: p.ai_description_translations || {},
    };
    loadLang('en');
    tagsString.value = (p.tags || []).join(', ');
    regionsString.value = (p.region_availability || []).join(', ');
    images.value = (p.images || []).map((i: any) => ({ key: i.key || '', url: i.url || '', alt: i.alt || '' }));
    variants.value = p.variants || [];
  } catch { error.value = t('common.loadFailed'); }
});

async function handleUpload({ file: fileItem }: any) {
  uploading.value = true;
  error.value = '';
  const file = fileItem.file as File;

  if (isEdit.value) {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await post(
        `/api/admin/v1/products/${route.params.id}/upload-image`,
        formData,
        { 'Content-Type': 'multipart/form-data' },
      );
      const uploaded = (res.data?.data?.images || res.data?.images || []).slice(-1)[0];
      if (uploaded) images.value.push({ key: uploaded.key || '', url: uploaded.url || '', alt: uploaded.alt || '' });
    } catch (e: any) { error.value = e.response?.data?.detail || t('common.uploadFailed') + ': ' + file.name; }
  } else {
    pendingFiles.value.push(file);
    images.value.push({ key: '', url: URL.createObjectURL(file), alt: '' });
  }
  uploading.value = false;
}

async function removeImage(idx: number) {
  if (isEdit.value) {
    const img = images.value[idx];
    if (!img.key) { images.value.splice(idx, 1); return; }
    try {
      await del(`/api/admin/v1/products/${route.params.id}/images/${encodeURIComponent(img.key)}`);
    } catch (e: any) {
      if (e.response?.status !== 404) { error.value = e.response?.data?.detail || t('common.deleteFailed'); return; }
    }
  } else {
    pendingFiles.value.splice(idx, 1);
  }
  images.value.splice(idx, 1);
}

async function save() {
  saving.value = true;
  error.value = '';
  syncLang('name'); syncLang('desc'); syncLang('ai');
  try {
    if (isEdit.value) {
      await patch(`/api/admin/v1/products/${route.params.id}`, form.value);
    } else {
      const res = await post('/api/admin/v1/products/', form.value);
      const newId = res.data?.data?.id ?? res.data?.id;
      for (const file of pendingFiles.value) {
        const formData = new FormData();
        formData.append('file', file);
        await post(
          `/api/admin/v1/products/${newId}/upload-image`,
          formData,
          { 'Content-Type': 'multipart/form-data' },
        );
      }
    }
    router.push('/products');
  } catch (e: any) { error.value = e.response?.data?.detail || t('common.saveFailed'); }
  finally { saving.value = false; }
}

async function changeStatus() {
  if (!statusChange.value) return;
  try {
    await post(`/api/admin/v1/products/${route.params.id}/status`, { status: statusChange.value });
    statusChange.value = null;
    router.push('/products');
  } catch (e: any) { error.value = e.response?.data?.detail || t('page.productsDetail.statusUpdateFailed'); }
}

function openVariantModal(v?: any) {
  if (v) {
    variantModal.value.id = v.id;
    variantForm.value = {
      sku: v.sku || '', name: v.name || '',
      attributesText: v.attributes && Object.keys(v.attributes).length ? JSON.stringify(v.attributes) : '',
      price: v.price ?? 0, cost: v.cost ?? 0, inventory: v.inventory ?? 0,
      status: v.status || 'active', is_default: !!v.is_default,
    };
  } else {
    variantModal.value.id = '';
    variantForm.value = {
      sku: '', name: '', attributesText: '',
      price: 0, cost: 0, inventory: 0, status: 'active', is_default: false,
    };
  }
  variantModal.value.show = true;
}

async function saveVariant() {
  variantSaving.value = true;
  error.value = '';
  let attributes: Record<string, any> | undefined;
  const attrText = variantForm.value.attributesText.trim();
  if (attrText) {
    try {
      attributes = JSON.parse(attrText);
      if (typeof attributes !== 'object' || attributes === null || Array.isArray(attributes)) throw new Error('bad');
    } catch {
      error.value = '属性必须是合法 JSON 对象';
      variantSaving.value = false;
      return;
    }
  } else {
    attributes = {};
  }
  const payload: any = {
    sku: variantForm.value.sku.trim(),
    name: variantForm.value.name.trim(),
    attributes,
    price: variantForm.value.price,
    cost: variantForm.value.cost,
    inventory: variantForm.value.inventory,
    status: variantForm.value.status,
    is_default: variantForm.value.is_default,
  };
  try {
    if (variantModal.value.id) {
      await patch(`/api/admin/v1/products/${route.params.id}/variants/${variantModal.value.id}`, payload);
    } else {
      await post(`/api/admin/v1/products/${route.params.id}/variants`, payload);
    }
    await reloadVariants();
    variantModal.value.show = false;
  } catch (e: any) { error.value = e.response?.data?.detail || '变体保存失败'; }
  finally { variantSaving.value = false; }
}

async function deleteVariant(id: string) {
  try {
    await del(`/api/admin/v1/products/${route.params.id}/variants/${id}`);
    await reloadVariants();
  } catch (e: any) { error.value = e.response?.data?.detail || '变体删除失败'; }
}

async function reloadVariants() {
  const res = await get(`/api/admin/v1/products/${route.params.id}/variants`);
  variants.value = res.data?.data ?? res.data ?? [];
}
</script>
