<template>
  <div class="property-panel h-full overflow-y-auto rounded bg-white p-4 shadow-sm dark:bg-dark">
    <!-- 选中元素信息面板（元素选择模式下，优先级最高） -->
    <template v-if="selectedElement">
      <div class="mb-4 flex items-center gap-2 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
        <SvgIcon icon="mdi:cursor-default-click" class="text-18px text-blue-600" />
        <span class="font-semibold">选中元素</span>
        <NButton size="tiny" quaternary type="error" class="ml-auto" @click="clearSelectedElement">
          <template #icon><SvgIcon icon="mdi:close" /></template>
        </NButton>
      </div>

      <!-- 元素信息（只读） -->
      <div class="mb-4 flex flex-col gap-2 rounded bg-gray-50 p-2 text-xs dark:bg-gray-800">
        <div class="flex items-center gap-2">
          <span class="text-gray-500">标签:</span>
          <span class="font-mono font-medium">{{ selectedElement.tag }}</span>
          <span class="text-gray-400">·</span>
          <span class="font-mono">{{ selectedElement.rect.width }}×{{ selectedElement.rect.height }}</span>
        </div>
        <div v-if="selectedElement.id" class="flex items-center gap-2">
          <span class="text-gray-500">ID:</span>
          <span class="font-mono">#{{ selectedElement.id }}</span>
        </div>
        <div v-if="selectedElement.classes.length" class="flex items-start gap-2">
          <span class="text-gray-500 shrink-0">类:</span>
          <div class="flex flex-wrap gap-1">
            <span v-for="cls in selectedElement.classes" :key="cls" class="font-mono rounded bg-blue-100 px-1 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">.{{ cls }}</span>
          </div>
        </div>
        <div v-if="selectedElement.textContent" class="flex items-start gap-2">
          <span class="text-gray-500 shrink-0">文本:</span>
          <span class="flex-1 truncate" :title="selectedElement.textContent">{{ selectedElement.textContent }}</span>
        </div>
        <div class="flex items-start gap-2">
          <span class="text-gray-500 shrink-0">选择器:</span>
          <span class="flex-1 break-all font-mono text-[10px] leading-tight">{{ selectedElement.selector }}</span>
        </div>
      </div>

      <!-- 提示：选择后的具体功能待规划 -->
      <div class="rounded border border-dashed border-gray-200 border-solid p-3 text-xs text-gray-400 dark:border-gray-700">
        <SvgIcon icon="mdi:information-outline" class="mr-1 text-14px" />
        元素选择后的操作功能规划中
      </div>
    </template>

    <!-- 站点配置面板（选中站点配置项时） -->
    <template v-else-if="activeConfigKey">
      <div class="mb-4 flex items-center gap-2 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
        <SvgIcon icon="mdi:cog-outline" class="text-18px text-green-600" />
        <span class="font-semibold">{{ configLabel }}</span>
        <NButton size="tiny" type="primary" class="ml-auto" :loading="saving" @click="handleSaveSiteConfig">保存站点配置</NButton>
      </div>

      <!-- 品牌 -->
      <div v-if="activeConfigKey === 'brand'" class="flex flex-col gap-3">
        <label class="text-xs font-medium text-gray-500">品牌名称</label>
        <NInput v-model:value="config.brand.name" />
        <label class="text-xs font-medium text-gray-500">标语 Tagline</label>
        <NInput v-model:value="config.brand.tagline" placeholder="可留空" />
        <label class="text-xs font-medium text-gray-500">Logo 类型</label>
        <NSelect v-model:value="config.brand.logo.type" :options="[{label:'文字',value:'text'},{label:'图片',value:'image'}]" size="small" />
        <template v-if="config.brand.logo.type === 'text'">
          <label class="text-xs font-medium text-gray-500">Logo 文字</label>
          <NInput v-model:value="config.brand.logo.data" placeholder="品牌文字 Logo" />
        </template>
        <template v-else>
          <label class="text-xs font-medium text-gray-500">上传 Logo 图片</label>
          <NUpload
            :show-file-list="false"
            accept="image/*"
            :custom-request="handleLogoUpload"
          >
            <NButton size="small" :loading="uploading">
              <template #icon><SvgIcon icon="mdi:upload" /></template>
              选择图片上传
            </NButton>
          </NUpload>
          <div v-if="config.brand.logo.data" class="flex items-center gap-2 rounded border border-gray-200 border-solid bg-gray-50 p-2">
            <img :src="config.brand.logo.data" class="h-10 w-10 rounded object-cover" alt="Logo" />
            <span class="flex-1 truncate text-xs text-gray-500">{{ config.brand.logo.data }}</span>
            <NButton size="tiny" quaternary type="error" @click="config.brand.logo.data = ''">
              <template #icon><SvgIcon icon="mdi:close" /></template>
            </NButton>
          </div>
          <label class="text-xs font-medium text-gray-500">或手动输入图片 URL</label>
          <NInput v-model:value="config.brand.logo.data" placeholder="https://example.com/logo.png" />
        </template>
      </div>

      <!-- 主题 -->
      <div v-else-if="activeConfigKey === 'theme'" class="flex flex-col gap-3">
        <label class="text-xs font-medium text-gray-500">主色 Primary</label>
        <div class="flex items-center gap-2">
          <NColorPicker :value="config.theme.primaryColor" @update:value="v => (config.theme.primaryColor = v)" size="small" />
          <NInput v-model:value="config.theme.primaryColor" size="small" style="flex:1" />
        </div>
        <label class="text-xs font-medium text-gray-500">浅主色 Primary Light</label>
        <div class="flex items-center gap-2">
          <NColorPicker :value="config.theme.primaryLight" @update:value="v => (config.theme.primaryLight = v)" size="small" />
          <NInput v-model:value="config.theme.primaryLight" size="small" style="flex:1" />
        </div>
        <label class="text-xs font-medium text-gray-500">深主色 Primary Dark</label>
        <div class="flex items-center gap-2">
          <NColorPicker :value="config.theme.primaryDark" @update:value="v => (config.theme.primaryDark = v)" size="small" />
          <NInput v-model:value="config.theme.primaryDark" size="small" style="flex:1" />
        </div>
        <label class="text-xs font-medium text-gray-500">辅助色 Secondary</label>
        <div class="flex items-center gap-2">
          <NColorPicker :value="config.theme.secondaryColor" @update:value="v => (config.theme.secondaryColor = v)" size="small" />
          <NInput v-model:value="config.theme.secondaryColor" size="small" style="flex:1" />
        </div>
        <label class="text-xs font-medium text-gray-500">强调色 Accent</label>
        <div class="flex items-center gap-2">
          <NColorPicker :value="config.theme.accentColor" @update:value="v => (config.theme.accentColor = v)" size="small" />
          <NInput v-model:value="config.theme.accentColor" size="small" style="flex:1" />
        </div>
        <label class="text-xs font-medium text-gray-500">标题字体</label>
        <NInput v-model:value="config.theme.fontHeading" />
        <label class="text-xs font-medium text-gray-500">正文字体</label>
        <NInput v-model:value="config.theme.fontBody" />
      </div>

      <!-- 导航 -->
      <div v-else-if="activeConfigKey === 'nav'" class="flex flex-col gap-2">
        <div v-for="(navItem, idx) in config.nav" :key="idx" class="flex items-center gap-2">
          <NInput v-model:value="navItem.label" size="small" placeholder="导航名称" style="flex:1" />
          <NInput v-model:value="navItem.url" size="small" placeholder="/path" style="flex:1" />
          <NButton size="tiny" quaternary type="error" @click="config.nav.splice(idx, 1)">
            <template #icon><SvgIcon icon="mdi:close" /></template>
          </NButton>
        </div>
        <NButton size="small" dashed @click="config.nav.push({label:'',url:''})">
          <template #icon><SvgIcon icon="mdi:plus" /></template>
          添加导航项
        </NButton>
      </div>

      <!-- 分类 -->
      <div v-else-if="activeConfigKey === 'categories'" class="flex flex-col gap-2">
        <div v-for="(cat, idx) in config.categories" :key="idx" class="flex items-center gap-2">
          <NInput v-model:value="cat.slug" size="small" placeholder="slug" style="flex:1" />
          <NInput v-model:value="cat.nameKey" size="small" placeholder="i18n key" style="flex:1" />
          <NInput v-model:value="cat.icon" size="small" placeholder="mdi:icon" style="width:100px" />
          <NButton size="tiny" quaternary type="error" @click="config.categories.splice(idx, 1)">
            <template #icon><SvgIcon icon="mdi:close" /></template>
          </NButton>
        </div>
        <NButton size="small" dashed @click="config.categories.push({slug:'',nameKey:'',icon:''})">
          <template #icon><SvgIcon icon="mdi:plus" /></template>
          添加分类
        </NButton>
      </div>

      <!-- 页脚 -->
      <div v-else-if="activeConfigKey === 'footer'" class="flex flex-col gap-3">
        <label class="text-xs font-medium text-gray-500">版权信息</label>
        <NInput v-model:value="config.footer.copyright" placeholder="© 2026 Forge. 版权所有。" />
        <label class="text-xs font-medium text-gray-500">订阅 Newsletter</label>
        <NSwitch v-model:value="config.footer.newsletter" />
      </div>

      <!-- SEO -->
      <div v-else-if="activeConfigKey === 'seo'" class="flex flex-col gap-3">
        <label class="text-xs font-medium text-gray-500">首页标题</label>
        <NInput v-model:value="config.seo.homeTitle" placeholder="首页 SEO 标题" />
        <label class="text-xs font-medium text-gray-500">Meta 描述</label>
        <NInput v-model:value="config.seo.metaDescription" type="textarea" placeholder="页面描述" />
        <label class="text-xs font-medium text-gray-500">Meta 关键词</label>
        <NInput v-model:value="config.seo.metaKeywords" placeholder="关键词, 用逗号分隔" />
      </div>

      <!-- i18n -->
      <div v-else-if="activeConfigKey === 'i18n'" class="flex flex-col gap-3">
        <label class="text-xs font-medium text-gray-500">默认语言</label>
        <NSelect v-model:value="config.i18n.defaultLocale" :options="localeOptions" size="small" />
        <label class="text-xs font-medium text-gray-500">支持语言</label>
        <NSelect v-model:value="config.i18n.locales" :options="localeOptions" multiple size="small" />
      </div>

      <!-- 功能开关 -->
      <div v-else-if="activeConfigKey === 'featureFlags'" class="flex flex-col gap-3">
        <div v-for="(val, key) in config.featureFlags" :key="key" class="flex items-center justify-between">
          <span class="text-sm">{{ key }}</span>
          <NSwitch v-model:value="config.featureFlags[key]" />
        </div>
        <div class="flex items-center gap-2">
          <NInput v-model:value="newFlagKey" size="small" placeholder="开关名称" style="flex:1" />
          <NButton size="small" @click="addFlag">添加</NButton>
        </div>
      </div>

      <!-- 货币 -->
      <div v-else-if="activeConfigKey === 'currencies'" class="flex flex-col gap-2">
        <div v-for="(cur, idx) in config.currencies" :key="idx" class="flex items-center gap-2">
          <NInput v-model:value="config.currencies[idx]" size="small" placeholder="如 USD" style="flex:1" />
          <NButton size="tiny" quaternary type="error" @click="config.currencies.splice(idx, 1)">
            <template #icon><SvgIcon icon="mdi:close" /></template>
          </NButton>
        </div>
        <NButton size="small" dashed @click="config.currencies.push('')">
          <template #icon><SvgIcon icon="mdi:plus" /></template>
          添加货币
        </NButton>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="flex h-full flex-col items-center justify-center gap-3 text-gray-400">
      <SvgIcon icon="mdi:cog-outline" class="text-48px" />
      <span class="text-sm">请从左侧选择一个配置项</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  NButton,
  NColorPicker,
  NInput,
  NSelect,
  NSwitch,
  NUpload,
  type UploadCustomRequestOptions
} from 'naive-ui';
import { useDiyStore, SITE_CONFIG_ITEMS } from '@/store/modules/diy';
import type { SelectedElementInfo } from '@/store/modules/diy';
import { siteApi } from '@/service/api/diy';

const store = useDiyStore();

const activeConfigKey = computed(() => store.activeSiteConfigItem);

// ========== 选中元素（只读展示） ==========
const selectedElement = computed<SelectedElementInfo | null>(() => store.selectedElement);

function clearSelectedElement() {
  store.setSelectedElement(null);
}

// ========== 站点配置编辑 ==========
const configLabel = computed(() => {
  const item = SITE_CONFIG_ITEMS.find(i => i.key === activeConfigKey.value);
  return item?.label || '';
});

const config = computed(() => store.siteConfig);

const saving = ref(false);
const uploading = ref(false);
const newFlagKey = ref('');

const localeOptions = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh' },
  { label: '日本語', value: 'ja' },
  { label: '한국어', value: 'ko' },
  { label: 'Français', value: 'fr' },
  { label: 'Deutsch', value: 'de' },
  { label: 'Español', value: 'es' },
  { label: 'العربية', value: 'ar' }
];

function addFlag() {
  if (newFlagKey.value.trim()) {
    config.value.featureFlags[newFlagKey.value.trim()] = false;
    newFlagKey.value = '';
  }
}

async function handleSaveSiteConfig() {
  saving.value = true;
  try {
    await store.saveSiteConfig();
    window.$message?.success('站点配置已保存');
  } catch {
    window.$message?.error('保存失败');
  } finally {
    saving.value = false;
  }
}

async function handleLogoUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  uploading.value = true;
  try {
    const res = await siteApi.uploadImage(file.file as File);
    config.value.brand.logo.data = (res as any).data?.url || (res as any).url || '';
    onFinish();
  } catch {
    window.$message?.error('上传失败');
    onError();
  } finally {
    uploading.value = false;
  }
}
</script>
