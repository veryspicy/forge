<template>
  <div class="flex flex-col gap-4">
    <NCard :title="$t('page.site.siteConfiguration')" size="small">
      <NGrid :cols="2" :x-gap="16" :y-gap="12" responsive="screen">
        <NGi span="1 m:2">
          <NFormItem :label="$t('page.site.siteName')"><NInput v-model:value="form.site_name" /></NFormItem>
        </NGi>
        <NGi span="1 m:2">
          <NFormItem :label="$t('page.site.siteSlogan')"><NInput v-model:value="form.site_slogan" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem :label="$t('page.site.openRegistration')"><NSwitch v-model:value="form.open_registration" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem :label="$t('page.site.maintenanceMode')"><NSwitch v-model:value="form.maintenance_mode" /></NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem :label="$t('page.site.defaultTheme')">
            <NSelect v-model:value="form.default_theme" :options="themeOptions" />
          </NFormItem>
        </NGi>
        <NGi span="1">
          <NFormItem :label="$t('page.site.defaultLanguage')">
            <NSelect v-model:value="form.default_language" :options="langOptions" />
          </NFormItem>
        </NGi>
      </NGrid>
    </NCard>

    <div v-if="saveMsg" class="text-sm p-2 rounded" :class="saveError ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'">
      {{ saveMsg }}
    </div>

    <div class="flex justify-end">
      <NButton type="primary" :loading="saving" @click="save">{{ $t('page.site.saveSiteConfig') }}</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, reactive, onMounted } from 'vue';
import { NButton, NCard, NFormItem, NGi, NGrid, NInput, NSelect, NSwitch } from 'naive-ui';
import { get, put } from '@/service/api/helper';

const saving = ref(false);
const saveMsg = ref('');
const saveError = ref(false);
const { t } = useI18n();

const form = reactive({
  site_name: 'Forge',
  site_slogan: 'AI-powered pet product marketplace',
  open_registration: true,
  maintenance_mode: false,
  default_theme: 'light',
  default_language: 'en',
});

const themeOptions = [
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' },
  { label: 'Auto', value: 'auto' },
];

const langOptions = [
  { label: 'English', value: 'en' },
  { label: 'Arabic', value: 'ar' },
];

onMounted(async () => {
  try {
    const res = await get('/api/admin/v1/site');
    if (res.data) Object.assign(form, res.data);
  } catch (e) { console.error('Failed to load site config', e); }
});

async function save() {
  saving.value = true; saveMsg.value = ''; saveError.value = false;
  try {
    await put('/api/admin/v1/site', form);
    saveMsg.value = t('page.site.settingsSaveSuccess');
  } catch (e: any) {
    saveError.value = true;
    saveMsg.value = e.response?.data?.detail || 'Save failed';
  } finally { saving.value = false; }
}
</script>
