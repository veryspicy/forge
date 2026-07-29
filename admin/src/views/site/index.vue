<template>
  <div class="flex flex-col gap-4">
    <NCard size="small">
      <NTabs v-model:value="activeTab" type="line">
        <NTabPane name="brand" tab="Brand" />
        <NTabPane name="theme" tab="Theme" />
        <NTabPane name="navigation" tab="Navigation" />
        <NTabPane name="sections" tab="Sections" />
        <NTabPane name="categories" tab="Categories" />
        <NTabPane name="footer" tab="Footer" />
        <NTabPane name="seo" tab="SEO" />
        <NTabPane name="i18n" tab="i18n" />
        <NTabPane name="featureFlags" tab="Feature Flags" />
        <NTabPane name="currencies" tab="Currencies" />
      </NTabs>
    </NCard>

    <!-- Brand -->
    <NCard v-if="activeTab === 'brand'" title="Brand" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12">
        <NGi span="1">
          <NFormItem label="Site Name"><NInput v-model:value="config.brand.name" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Tagline"><NInput v-model:value="config.brand.tagline" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Logo Type">
            <NSelect v-model:value="config.brand.logo.type" :options="logoTypeOptions" />
          </NFormItem>
        </NGi>
        <NGi span="2">
          <NFormItem label="Logo Data (SVG string)"><NInput type="textarea" v-model:value="config.brand.logo.data" :rows="3" /></NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- Theme -->
    <NCard v-if="activeTab === 'theme'" title="Theme" size="small">
      <NGrid :cols="3" :x-gap="16" :y-gap="12">
        <NGi span="1">
          <NFormItem label="Primary"><NColorPicker v-model:value="config.theme.primaryColor" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Primary Light"><NColorPicker v-model:value="config.theme.primaryLight" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Primary Dark"><NColorPicker v-model:value="config.theme.primaryDark" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Secondary"><NColorPicker v-model:value="config.theme.secondaryColor" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Accent"><NColorPicker v-model:value="config.theme.accentColor" /></NFormItem>
        </NGi>
        <NGi span="1" />
        <NGi span="1">
          <NFormItem label="Heading Font"><NInput v-model:value="config.theme.fontHeading" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Body Font"><NInput v-model:value="config.theme.fontBody" /></NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- Navigation -->
    <NCard v-if="activeTab === 'navigation'" title="Navigation Links" size="small">
      <div class="flex flex-col gap-3">
        <div v-for="(nav, i) in config.navigation" :key="i" class="flex items-center gap-2">
          <NInput v-model:value="nav.key" placeholder="Key" style="width:120px" size="small" />
          <NInput v-model:value="nav.to" placeholder="URL" style="width:150px" size="small" />
          <NInput v-model:value="nav.labelKey" placeholder="Label i18n Key" style="width:150px" size="small" />
          <NSwitch v-model:value="nav.visible" size="small" />
          <NButton size="small" type="error" quaternary @click="config.navigation.splice(i, 1)">Remove</NButton>
        </div>
        <NButton size="small" dashed @click="config.navigation.push({ key: '', to: '/', labelKey: '', visible: true })">Add Link</NButton>
      </div>
    </NCard>

    <!-- Sections -->
    <NCard v-if="activeTab === 'sections'" title="Sections" size="small">
      <div class="flex flex-col gap-4">
        <div v-for="(sec, i) in config.sections" :key="i" class="border rounded p-3">
          <div class="flex items-center gap-4 mb-2">
            <NSwitch v-model:value="sec.visible" size="small" />
            <NInput v-model:value="sec.type" placeholder="Type" style="width:160px" size="small" />
            <NButton size="small" type="error" quaternary @click="config.sections.splice(i, 1)">Remove</NButton>
          </div>
          <!-- Section config fields (expandable) -->
          <div v-if="sec.visible" class="flex flex-col gap-2 mt-2 pl-2 border-l-2 border-gray-200">
            <template v-if="sec.type === 'hero'">
              <NFormItem label="Title Key" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.titleKey" size="small" /></NFormItem>
              <NFormItem label="Desc Key" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.descKey" size="small" /></NFormItem>
              <NFormItem label="Pri Btn Label" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.primaryButton.labelKey" size="small" /></NFormItem>
              <NFormItem label="Pri Btn URL" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.primaryButton.to" size="small" /></NFormItem>
              <NFormItem label="Sec Btn Label" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.secondaryButton.labelKey" size="small" /></NFormItem>
              <NFormItem label="Sec Btn URL" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.secondaryButton.to" size="small" /></NFormItem>
            </template>
            <template v-else-if="sec.type === 'ai_teaser'">
              <NFormItem label="Title Key" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.titleKey" size="small" /></NFormItem>
              <NFormItem label="Desc Key" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.descKey" size="small" /></NFormItem>
              <NFormItem label="Button Label" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.button.labelKey" size="small" /></NFormItem>
              <NFormItem label="Button URL" label-placement="left" :label-width="100" size="small"><NInput v-model:value="sec.config.button.to" size="small" /></NFormItem>
            </template>
            <template v-else>
              <span class="text-xs text-gray-400">No extra config for "{{ sec.type }}"</span>
            </template>
          </div>
        </div>
        <NButton size="small" dashed @click="config.sections.push({ type: '', visible: true, config: {} })">Add Section</NButton>
      </div>
    </NCard>

    <!-- Categories -->
    <NCard v-if="activeTab === 'categories'" title="Categories" size="small">
      <div class="flex flex-col gap-3">
        <div v-for="(cat, i) in config.categories" :key="i" class="flex items-center gap-2">
          <NInput v-model:value="cat.slug" placeholder="Slug" style="width:120px" size="small" />
          <NInput v-model:value="cat.nameKey" placeholder="i18n Key" style="width:140px" size="small" />
          <NInput v-model:value="cat.icon" placeholder="Icon/Emoji" style="width:100px" size="small" />
          <NButton size="small" type="error" quaternary @click="config.categories.splice(i, 1)">Remove</NButton>
        </div>
        <NButton size="small" dashed @click="config.categories.push({ slug: '', nameKey: '', icon: '' })">Add Category</NButton>
      </div>
    </NCard>

    <!-- Footer -->
    <NCard v-if="activeTab === 'footer'" title="Footer" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12">
        <NGi span="1">
          <NFormItem label="Newsletter Signup"><NSwitch v-model:value="config.footer.newsletter" /></NFormItem>
        </NGi>
        <NGi span="2">
          <NFormItem label="Column Layout">
            <NSelect v-model:value="config.footer.columns" multiple :options="footerColumnOptions" />
          </NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- SEO -->
    <NCard v-if="activeTab === 'seo'" title="SEO" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12">
        <NGi span="2">
          <NFormItem label="Title Template"><NInput v-model:value="config.seo.titleTemplate" placeholder="%s | Forge Pet Supplies" /></NFormItem>
        </NGi>
        <NGi span="2">
          <NFormItem label="Meta Description"><NInput type="textarea" v-model:value="config.seo.description" :rows="2" /></NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- i18n -->
    <NCard v-if="activeTab === 'i18n'" title="i18n" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12">
        <NGi span="1">
          <NFormItem label="Default Locale">
            <NSelect v-model:value="config.i18n.defaultLocale" :options="localeOptions" />
          </NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem label="Supported Locales">
            <NSelect v-model:value="config.i18n.locales" :options="localeOptions" multiple />
          </NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- Feature Flags -->
    <NCard v-if="activeTab === 'featureFlags'" title="Feature Flags" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12">
        <NGi span="1">
          <NSpace align="center"><NSwitch v-model:value="config.feature_flags.show_pets_page" /><span>My Pets Page</span></NSpace>
        </NGi>
        <NGi span="1">
          <NSpace align="center"><NSwitch v-model:value="config.feature_flags.show_ai_chat" /><span>AI Chat</span></NSpace>
        </NGi>
        <NGi span="1">
          <NSpace align="center"><NSwitch v-model:value="config.feature_flags.show_blog" /><span>Blog</span></NSpace>
        </NGi>
        <NGi span="1" />
        <NGi span="1">
          <NFormItem label="Cookie Prefix"><NInput v-model:value="config.feature_flags.cookie_prefix" size="small" /></NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- Currencies -->
    <NCard v-if="activeTab === 'currencies'" title="Currencies &amp; Regions" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12">
        <NGi span="2">
          <NFormItem label="Currencies">
            <NSelect v-model:value="config.currencies" multiple :options="currencyOptions" />
          </NFormItem>
        </NGi>
        <NGi span="2">
          <NFormItem label="Regions">
            <NSelect v-model:value="config.regions" multiple :options="regionOptions" />
          </NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <!-- Save feedback -->
    <div v-if="saveMsg" class="text-sm p-2 rounded" :class="saveError ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'">
      {{ saveMsg }}
    </div>

    <div class="flex justify-end">
      <NButton type="primary" :loading="saving" @click="save">Save Configuration</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import {
  NButton, NCard, NColorPicker, NFormItem, NGi, NGrid,
  NInput, NSelect, NSpace, NSwitch, NTabPane, NTabs,
} from 'naive-ui';
import { get, put } from '@/service/api/helper';

const saving = ref(false);
const saveMsg = ref('');
const saveError = ref(false);
const activeTab = ref('brand');

const config = reactive({
  brand: { name: 'Forge', tagline: '', logo: { type: 'svg', data: '' } },
  theme: { primaryColor: '#4f46e5', primaryLight: '#818cf8', primaryDark: '#3730a3', secondaryColor: '#ec4899', accentColor: '#f97316', fontHeading: 'Inter', fontBody: 'Inter' },
  navigation: [] as { key: string; to: string; labelKey: string; visible: boolean }[],
  sections: [] as { type: string; visible: boolean; config: Record<string, any> }[],
  categories: [] as { slug: string; nameKey: string; icon: string }[],
  footer: { columns: [] as string[], newsletter: true },
  seo: { titleTemplate: '%s | Forge', description: '' },
  i18n: { defaultLocale: 'en', locales: ['en'] as string[] },
  feature_flags: { show_pets_page: false, show_ai_chat: false, show_blog: false, cookie_prefix: 'forge' },
  currencies: ['USD'] as string[],
  regions: [] as string[],
});

const logoTypeOptions = [
  { label: 'SVG', value: 'svg' },
  { label: 'URL', value: 'url' },
];

const localeOptions = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh' },
  { label: 'العربية', value: 'ar' },
  { label: 'Deutsch', value: 'de' },
  { label: 'Français', value: 'fr' },
];

const footerColumnOptions = [
  { label: 'Shop', value: 'shop' },
  { label: 'Support', value: 'support' },
  { label: 'About', value: 'about' },
  { label: 'Legal', value: 'legal' },
];

const currencyOptions = [
  { label: 'USD', value: 'USD' },
  { label: 'EUR', value: 'EUR' },
  { label: 'GBP', value: 'GBP' },
  { label: 'CNY', value: 'CNY' },
  { label: 'JPY', value: 'JPY' },
];

const regionOptions = [
  { label: 'North America', value: 'na' },
  { label: 'Europe', value: 'eu' },
  { label: 'Asia Pacific', value: 'apac' },
  { label: 'Middle East', value: 'me' },
  { label: 'Latin America', value: 'latam' },
];

onMounted(async () => {
  try {
    const res: any = await get('/api/admin/v1/site');
    const remote = res.data?.config ?? res.data;
    if (!remote || typeof remote !== 'object') return;

    if (remote.brand) {
      if (remote.brand.name) config.brand.name = remote.brand.name;
      if (remote.brand.tagline) config.brand.tagline = remote.brand.tagline;
      if (remote.brand.logo) config.brand.logo = { ...config.brand.logo, ...remote.brand.logo };
    }
    if (remote.theme) Object.assign(config.theme, remote.theme);
    if (remote.navigation) config.navigation = remote.navigation;
    if (remote.sections) config.sections = remote.sections;
    if (remote.categories) config.categories = remote.categories;
    if (remote.footer) {
      if (remote.footer.columns) config.footer.columns = remote.footer.columns;
      if (typeof remote.footer.newsletter === 'boolean') config.footer.newsletter = remote.footer.newsletter;
    }
    if (remote.seo) Object.assign(config.seo, remote.seo);
    if (remote.i18n) {
      if (remote.i18n.defaultLocale) config.i18n.defaultLocale = remote.i18n.defaultLocale;
      if (remote.i18n.locales) config.i18n.locales = remote.i18n.locales;
    }
    if (remote.feature_flags) Object.assign(config.feature_flags, remote.feature_flags);
    if (remote.currencies) config.currencies = remote.currencies;
    if (remote.regions) config.regions = remote.regions;
  } catch (e) {
    console.error('Failed to load site config', e);
  }
});

async function save() {
  saving.value = true;
  saveMsg.value = '';
  saveError.value = false;
  try {
    await put('/api/admin/v1/site', { config: { ...config } });
    saveMsg.value = 'Settings saved successfully';
  } catch (e: any) {
    saveError.value = true;
    saveMsg.value = e.response?.data?.detail || e.message || 'Save failed';
  } finally {
    saving.value = false;
  }
}
</script>
