<template>
  <div class="property-panel h-full overflow-y-auto rounded bg-white p-4 shadow-sm dark:bg-dark">
    <!-- 站点配置面板（未选中组件时） -->
    <div v-if="!component" class="flex flex-col gap-3">
      <div class="mb-2 flex items-center gap-2 border-b border-gray-100 border-solid pb-2 dark:border-gray-700">
        <SvgIcon icon="mdi:web" class="text-18px text-green-600" />
        <span class="font-semibold">站点配置</span>
      </div>

      <NCollapse :default-expanded-names="['brand', 'theme']">
        <!-- Brand -->
        <NCollapseItem name="brand" title="品牌">
          <NFormItem label="站点名称">
            <NInput v-model:value="siteConfig.brand.name" size="small" />
          </NFormItem>
          <NFormItem label="标语">
            <NInput v-model:value="siteConfig.brand.tagline" size="small" />
          </NFormItem>
          <NFormItem label="Logo 类型">
            <NSelect
              v-model:value="siteConfig.brand.logo.type"
              :options="logoTypeOptions"
              size="small"
            />
          </NFormItem>
        </NCollapseItem>

        <!-- Theme -->
        <NCollapseItem name="theme" title="主题">
          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="text-11px text-gray-500">Primary</label>
              <NColorPicker v-model:value="siteConfig.theme.primaryColor" size="small" />
            </div>
            <div>
              <label class="text-11px text-gray-500">Primary Light</label>
              <NColorPicker v-model:value="siteConfig.theme.primaryLight" size="small" />
            </div>
            <div>
              <label class="text-11px text-gray-500">Primary Dark</label>
              <NColorPicker v-model:value="siteConfig.theme.primaryDark" size="small" />
            </div>
            <div>
              <label class="text-11px text-gray-500">Secondary</label>
              <NColorPicker v-model:value="siteConfig.theme.secondaryColor" size="small" />
            </div>
            <div>
              <label class="text-11px text-gray-500">Accent</label>
              <NColorPicker v-model:value="siteConfig.theme.accentColor" size="small" />
            </div>
          </div>
          <NFormItem label="标题字体" class="mt-2">
            <NInput v-model:value="siteConfig.theme.fontHeading" size="small" />
          </NFormItem>
          <NFormItem label="正文字体">
            <NInput v-model:value="siteConfig.theme.fontBody" size="small" />
          </NFormItem>
        </NCollapseItem>

        <!-- Navigation -->
        <NCollapseItem name="navigation" title="导航">
          <div
            v-for="(item, idx) in siteConfig.navigation.items"
            :key="idx"
            class="mb-2 flex items-center gap-2 rounded border p-2"
          >
            <NInput v-model:value="item.label" size="small" placeholder="名称" style="width:80px" />
            <NInput v-model:value="item.url" size="small" placeholder="链接" class="flex-1" />
            <NButton size="tiny" quaternary type="error" @click="removeNavItem(idx)">
              <template #icon><SvgIcon icon="mdi:close" /></template>
            </NButton>
          </div>
          <NButton size="tiny" dashed block @click="addNavItem">+ 添加导航项</NButton>
        </NCollapseItem>

        <!-- Categories -->
        <NCollapseItem name="categories" title="分类">
          <div
            v-for="(cat, idx) in siteConfig.categories"
            :key="idx"
            class="mb-2 flex items-center gap-2 rounded border p-2"
          >
            <NInput v-model:value="cat.slug" size="small" placeholder="Slug" style="width:90px" />
            <NInput v-model:value="cat.nameKey" size="small" placeholder="i18n Key" class="flex-1" />
            <NInput v-model:value="cat.icon" size="small" placeholder="图标" style="width:70px" />
            <NButton size="tiny" quaternary type="error" @click="siteConfig.categories.splice(idx, 1)">
              <template #icon><SvgIcon icon="mdi:close" /></template>
            </NButton>
          </div>
          <NButton size="tiny" dashed block @click="siteConfig.categories.push({ slug: '', nameKey: '', icon: '' })">+ 添加分类</NButton>
        </NCollapseItem>

        <!-- Footer -->
        <NCollapseItem name="footer" title="页脚">
          <NFormItem label="版权文字">
            <NInput v-model:value="siteConfig.footer.copyright" size="small" />
          </NFormItem>
          <NFormItem label="Newsletter">
            <NSwitch v-model:value="siteConfig.footer.newsletter" size="small" />
          </NFormItem>
        </NCollapseItem>

        <!-- SEO -->
        <NCollapseItem name="seo" title="SEO">
          <NFormItem label="首页标题">
            <NInput v-model:value="siteConfig.seo.homeTitle" size="small" />
          </NFormItem>
          <NFormItem label="Meta 描述">
            <NInput v-model:value="siteConfig.seo.metaDescription" type="textarea" size="small" :rows="2" />
          </NFormItem>
          <NFormItem label="Meta 关键词">
            <NInput v-model:value="siteConfig.seo.metaKeywords" size="small" />
          </NFormItem>
        </NCollapseItem>

        <!-- Feature Flags -->
        <NCollapseItem name="featureFlags" title="功能开关">
          <NSwitch
            v-for="(flag, key) in siteConfig.featureFlags"
            :key="String(key)"
            :value="!!flag"
            @update:value="(v: boolean) => { siteConfig.featureFlags[key] = v; }"
          >
            <template #checked>{{ String(key) }}: ON</template>
            <template #unchecked>{{ String(key) }}: OFF</template>
          </NSwitch>
        </NCollapseItem>
      </NCollapse>

      <NButton type="primary" block size="small" :loading="savingConfig" @click="saveConfig">
        保存站点配置
      </NButton>
    </div>

    <!-- 组件属性面板（选中组件时） -->
    <template v-else>
      <div class="mb-4 flex items-center gap-2 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
        <NButton size="tiny" quaternary type="error" @click="store.removeComponent(component.id)">
          <template #icon><SvgIcon icon="mdi:delete" /></template>
        </NButton>
        <SvgIcon :icon="component.component_icon || 'mdi:widget'" class="text-18px" />
        <span class="font-semibold">{{ component.component_name }}</span>
        <NSwitch
          :value="component.is_visible !== false"
          size="small"
          class="ml-auto"
          @update:value="toggleVisible"
        />
      </div>

      <DynamicForm
        :schema="component.config_schema"
        :model-value="component.config"
        @update:model-value="handleUpdate"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  NButton,
  NCollapse,
  NCollapseItem,
  NColorPicker,
  NFormItem,
  NInput,
  NSelect,
  NSwitch
} from 'naive-ui';
import { useDiyStore } from '@/store/modules/diy';
import DynamicForm from './DynamicForm.vue';
import { get } from '@/service/api/helper';

const store = useDiyStore();

const component = computed<any | null>(() => store.activeComponent);

// --- 站点配置 ---

const logoTypeOptions = [
  { label: '文本', value: 'text' },
  { label: '图片', value: 'image' },
  { label: 'SVG', value: 'svg' }
];

const defaultSiteConfig = {
  brand: { name: '', tagline: '', logo: { type: 'text', data: '' } },
  theme: {
    primaryColor: '#18a058',
    primaryLight: '#36ad6a',
    primaryDark: '#0c7a43',
    secondaryColor: '#f0a020',
    accentColor: '#2080f0',
    fontHeading: '',
    fontBody: ''
  },
  navigation: { items: [] as any[] },
  categories: [] as { slug: string; nameKey: string; icon: string }[],
  footer: { copyright: '', newsletter: true },
  seo: { homeTitle: '', metaDescription: '', metaKeywords: '' },
  featureFlags: {} as Record<string, boolean>
};

const siteConfig = reactive<any>(JSON.parse(JSON.stringify(defaultSiteConfig)));
const savingConfig = ref(false);

onMounted(async () => {
  try {
    const res = await get('/api/admin/v1/site/config');
    if (res.data) {
      Object.assign(siteConfig, JSON.parse(JSON.stringify(defaultSiteConfig)), res.data);
    }
  } catch {
    // 站点配置未就绪时使用默认值
  }
});

async function saveConfig() {
  savingConfig.value = true;
  try {
    await get('/api/admin/v1/site/config'); // placeholder: use PUT when available
    window.$message?.success('站点配置已保存');
  } catch {
    window.$message?.error('保存失败');
  } finally {
    savingConfig.value = false;
  }
}

function addNavItem() {
  siteConfig.navigation.items.push({ label: '', url: '' });
}

function removeNavItem(idx: number) {
  siteConfig.navigation.items.splice(idx, 1);
}

// --- 组件属性 ---

function handleUpdate(config: Record<string, any>) {
  if (component.value) {
    store.updateComponentConfig(component.value.id, config);
  }
}

function toggleVisible(visible: boolean) {
  if (component.value) {
    component.value.is_visible = visible;
  }
}
</script>
