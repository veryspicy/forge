<template>
  <div class="property-panel h-full overflow-y-auto rounded bg-white p-4 shadow-sm dark:bg-dark">
    <template v-if="selectedElement">
      <div class="mb-4 flex items-center gap-2 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
        <SvgIcon icon="mdi:cursor-default-click" class="text-18px text-blue-600" />
        <span class="font-semibold">选中元素</span>
        <NButton size="tiny" quaternary type="error" class="ml-auto" @click="clearSelectedElement">
          <template #icon><SvgIcon icon="mdi:close" /></template>
        </NButton>
      </div>
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
      <div class="rounded border border-dashed border-gray-200 border-solid p-3 text-xs text-gray-400 dark:border-gray-700">
        <SvgIcon icon="mdi:information-outline" class="mr-1 text-14px" />
        元素选择后的操作功能规划中
      </div>
    </template>

    <template v-else-if="activeConfigKey">
      <div class="mb-4 flex items-center gap-2 border-b border-gray-100 border-solid pb-3 dark:border-gray-700">
        <SvgIcon icon="mdi:cog-outline" class="text-18px text-green-600" />
        <span class="font-semibold">{{ configLabel }}</span>
        <NButton size="tiny" type="primary" class="ml-auto" :loading="saving" @click="handleSaveSiteConfig">保存站点配置</NButton>
      </div>

      <!-- 1. 品牌配置 -->
      <div v-if="activeConfigKey === 'brand'" class="flex flex-col gap-3">
        <FieldLabel label="品牌名称" name="name" type="string" range="≤ 50 字符" example="Forge" desc="品牌名称，显示在站点页头/页脚及浏览器标题。" />
        <NInput v-model:value="config.brand.name" placeholder="请输入品牌名称" />
        <FieldLabel label="品牌标语" name="tagline" type="string" range="≤ 120 字符" example="AI 驱动的宠物用品商店" desc="一句话品牌介绍（可留空），显示在页头副标题区域。" />
        <NInput v-model:value="config.brand.tagline" placeholder="一句话品牌介绍（可留空）" />
        <FieldLabel label="Logo 类型" name="logo.type" type="enum" range="text | image | svg" example="text" desc="Logo 渲染方式：文字 / 图片 / 内联 SVG 代码。" />
        <NSelect
          v-model:value="config.brand.logo.type"
          :options="[
            { label:'文字 Logo', value:'text' },
            { label:'图片 Logo', value:'image' },
            { label:'SVG 代码', value:'svg' }
          ]"
          size="small"
        />
        <template v-if="config.brand.logo.type === 'text'">
          <FieldLabel label="Logo 文字" name="logo.data" type="string" range="≤ 30 字符" example="Forge" desc="显示在 Logo 位置的文字。" />
          <NInput v-model:value="config.brand.logo.data" placeholder="显示在 Logo 位置的文字" />
        </template>
        <template v-else-if="config.brand.logo.type === 'image'">
          <FieldLabel label="Logo 图片" name="logo.data" type="image URL" range="http(s):// 或 data:image" example="https://example.com/logo.png" desc="上传 Logo 图片，或手动输入图片 URL。" />
          <NUpload :show-file-list="false" accept="image/*" :custom-request="(opt) => handleImageUpload(opt, { target: 'brandLogo' })">
            <NButton size="small" :loading="uploadingBrandLogo">
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
          <FieldLabel label="Logo 图片 URL" name="logo.data (URL)" type="string" range="http(s)://" example="https://example.com/logo.png" desc="或手动输入图片 URL。" />
          <NInput v-model:value="config.brand.logo.data" placeholder="https://example.com/logo.png" />
        </template>
        <template v-else-if="config.brand.logo.type === 'svg'">
          <FieldLabel label="Logo SVG 代码" name="logo.data" type="string (SVG)" range="合法 SVG 源码" example='<svg viewBox="0 0 100 100">...</svg>' desc="粘贴 SVG 源码，将过滤 script / on* 等注入后实时预览。" />
          <NInput
            v-model:value="config.brand.logo.data"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 16 }"
            placeholder='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">...</svg>'
            class="font-mono text-[11px] leading-5"
          />
          <div class="flex flex-col gap-2 rounded border border-dashed border-gray-200 border-solid bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <span class="text-[11px] text-gray-400">实时预览（已过滤 script / on* 等注入）</span>
              <NButton
                size="tiny"
                quaternary
                type="error"
                @click="config.brand.logo.data = ''"
                v-if="config.brand.logo.data"
              >
                <template #icon><SvgIcon icon="mdi:close" /></template>
                清空
              </NButton>
            </div>
            <div
              v-if="brandSvgPreview"
              class="flex h-14 w-full items-center justify-center rounded border border-gray-200 border-solid bg-white p-2 dark:border-gray-700 dark:bg-dark"
            >
              <div
                class="h-full w-auto [&>svg]:h-full [&>svg]:w-auto [&>svg]:max-h-full"
                v-html="brandSvgPreview"
              />
            </div>
            <div
              v-else
              class="flex h-14 w-full items-center justify-center rounded border border-dashed border-gray-200 border-solid text-[11px] text-gray-400 dark:border-gray-700"
            >
              暂无 SVG 代码
            </div>
          </div>
        </template>
      </div>

      <!-- 2. 主题配置 -->
      <div v-else-if="activeConfigKey === 'theme'" class="flex flex-col gap-4">
        <FieldLabel label="主题预设" name="preset" type="enum" range="forge | apple | cloudflare | linear | vercel | stripe | notik | shopify" example="forge" desc="一键套用预置配色方案，点击后覆盖下方各色值。" />
        <div class="grid grid-cols-2 gap-2">
          <div
            v-for="(preset, presetKey) in THEME_PRESETS"
            :key="presetKey"
            class="cursor-pointer rounded-lg border-2 border-solid p-2 transition-all"
            :class="config.theme.preset === presetKey ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-200 hover:border-gray-300 dark:border-gray-700'"
            @click="applyThemePreset(presetKey as string)"
          >
            <div class="mb-1 flex items-center gap-1">
              <div v-for="(color, ci) in preset.swatch" :key="ci" class="h-4 w-4 rounded" :style="{ backgroundColor: color }" />
            </div>
            <div class="text-xs font-medium">{{ preset.label }}</div>
          </div>
        </div>
        <div class="border-t border-gray-100 border-solid pt-3 dark:border-gray-700" />
        <div class="flex flex-col gap-3">
          <FieldLabel label="主色" name="primaryColor" type="hex color" range="#000000 ~ #ffffff" example="#18a058" desc="主题主色，用于按钮/链接/选中态等核心交互元素。" />
          <div class="flex items-center gap-2">
            <NColorPicker :value="config.theme.primaryColor" @update:value="v => (config.theme.primaryColor = v)" size="small" />
            <NInput v-model:value="config.theme.primaryColor" size="small" style="flex:1" />
          </div>
          <FieldLabel label="主色浅变体" name="primaryLight" type="hex color" range="#000000 ~ #ffffff" example="#36ad6a" desc="主色的浅色变体，用于 hover 状态 / 浅色背景。" />
          <div class="flex items-center gap-2">
            <NColorPicker :value="config.theme.primaryLight" @update:value="v => (config.theme.primaryLight = v)" size="small" />
            <NInput v-model:value="config.theme.primaryLight" size="small" style="flex:1" />
          </div>
          <FieldLabel label="主色深变体" name="primaryDark" type="hex color" range="#000000 ~ #ffffff" example="#0c7a43" desc="主色的深色变体，用于 active 状态 / 强调文字。" />
          <div class="flex items-center gap-2">
            <NColorPicker :value="config.theme.primaryDark" @update:value="v => (config.theme.primaryDark = v)" size="small" />
            <NInput v-model:value="config.theme.primaryDark" size="small" style="flex:1" />
          </div>
          <FieldLabel label="辅助色" name="secondaryColor" type="hex color" range="#000000 ~ #ffffff" example="#f0a020" desc="辅助色，用于次要按钮 / 标签 / 价格等。" />
          <div class="flex items-center gap-2">
            <NColorPicker :value="config.theme.secondaryColor" @update:value="v => (config.theme.secondaryColor = v)" size="small" />
            <NInput v-model:value="config.theme.secondaryColor" size="small" style="flex:1" />
          </div>
          <FieldLabel label="强调色" name="accentColor" type="hex color" range="#000000 ~ #ffffff" example="#2080f0" desc="强调色，用于促销/提示/链接等需要突出的元素。" />
          <div class="flex items-center gap-2">
            <NColorPicker :value="config.theme.accentColor" @update:value="v => (config.theme.accentColor = v)" size="small" />
            <NInput v-model:value="config.theme.accentColor" size="small" style="flex:1" />
          </div>
          <FieldLabel label="标题字体" name="fontHeading" type="string (font-family)" range="CSS font-family 值" example="Inter, sans-serif" desc="标题字体栈，可填 Google Fonts 字体名 + 兜底字体。" />
          <NInput v-model:value="config.theme.fontHeading" placeholder="如 Inter, sans-serif" />
          <FieldLabel label="正文字体" name="fontBody" type="string (font-family)" range="CSS font-family 值" example="Inter, sans-serif" desc="正文字体栈，可填 Google Fonts 字体名 + 兜底字体。" />
          <NInput v-model:value="config.theme.fontBody" placeholder="如 Inter, sans-serif" />
        </div>
      </div>

      <!-- 3. 导航配置（新版：可折叠卡片 + feature flag 联动 + 快捷预设） -->
      <div v-else-if="activeConfigKey === 'navigation'" class="flex flex-col gap-3">
        <!-- 快捷预设按钮 -->
        <div class="flex flex-wrap items-center gap-1 rounded border border-dashed border-gray-200 border-solid bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800">
          <span class="mr-1 text-[11px] text-gray-400">快捷添加：</span>
          <NButton
            v-for="preset in NAV_PRESETS"
            :key="preset.to"
            size="tiny"
            quaternary
            type="primary"
            @click="addNavPreset(preset)"
          >
            {{ preset.label }}
          </NButton>
        </div>

        <!-- 公共前缀置顶：导航项 i18n key 统一以 nav. 开头，下方只需填后缀 -->
        <div class="rounded border border-dashed border-gray-200 border-solid p-2 text-[11px] leading-relaxed text-gray-400 dark:border-gray-700">
          🔑 公共前缀：导航翻译 key 统一以 <b>nav.</b> 开头，下方每个导航项的「翻译 Key 后缀」只需填写后半段，保存时自动拼接（如 <code>myPets</code> → <code>nav.myPets</code>）。
        </div>

        <template v-if="config.navigation.length === 0">
          <div class="rounded border border-dashed border-gray-200 border-solid p-6 text-center text-sm text-gray-400 dark:border-gray-700">
            暂无导航项，点击下方按钮添加或使用上方快捷预设
          </div>
        </template>

        <VueDraggable v-model="config.navigation" handle=".nav-drag-handle" :animation="150" class="flex flex-col gap-2">
          <div
            v-for="(navItem, idx) in config.navigation"
            :key="navItem.key || idx"
            class="overflow-hidden rounded border border-gray-200 border-solid transition-all dark:border-gray-700"
            :class="navItem.visible ? '' : 'opacity-60'"
          >
            <!-- 卡片顶栏：拖拽 / 显隐 / 名称 一行展示 -->
            <div class="flex items-center gap-2 bg-gray-50 px-2 py-2 dark:bg-gray-800/60">
              <SvgIcon icon="mdi:drag-vertical" class="nav-drag-handle cursor-grab text-gray-400 hover:text-gray-600" />
              <NSwitch v-model:value="navItem.visible" size="small" />
              <NInput
                v-model:value="navItem.label"
                size="small"
                placeholder="导航名称（例如：我的宠物）"
                style="flex:1"
                @update:value="v => onNavLabelChanged(idx, v)"
              />
              <NTag v-if="navItem.featureFlag" size="small" type="info" :bordered="false">
                ⚡ {{ navItem.featureFlag }}
              </NTag>
              <NButton
                size="tiny"
                quaternary
                @click="navItem._open = !navItem._open"
                :title="navItem._open ? '收起' : '展开更多'"
              >
                <template #icon>
                  <SvgIcon :icon="navItem._open ? 'mdi:chevron-up' : 'mdi:chevron-down'" />
                </template>
              </NButton>
              <NButton
                size="tiny"
                quaternary
                type="error"
                @click="config.navigation.splice(idx, 1)"
              >
                <template #icon><SvgIcon icon="mdi:close" /></template>
              </NButton>
            </div>

            <!-- 展开的详细配置 -->
            <div v-if="navItem._open !== false" class="flex flex-col gap-3 p-2">
              <div class="flex flex-col gap-1">
                <FieldLabel label="跳转路径" name="to" type="string" range="站内路径，/ 开头" example="/products" desc="导航项点击跳转的站内路由路径。" />
                <NSelect
                  v-model:value="navItem.to"
                  filterable
                  allow-input
                  :options="PATH_OPTIONS"
                  size="small"
                  placeholder="选择或输入路径"
                />
              </div>
              <div class="flex flex-col gap-1">
                <FieldLabel label="翻译 Key 后缀" name="labelKey" type="string" range="自动拼接 nav. 前缀" example="myPets" desc="导航 i18n key 统一以 nav. 开头（公共前缀已置顶展示），此处只填后缀，保存时自动拼接为 nav.myPets；留空则按名称自动生成。" />
                <div class="flex items-center gap-1">
                  <NTag size="small" type="info" :bordered="false" class="shrink-0" title="导航 i18n key 公共前缀，自动拼接">nav.</NTag>
                  <NInput :value="navKeySuffix(navItem.labelKey)" @update:value="v => onNavLabelKeyChanged(idx, navItem.labelKey, v)" size="small" placeholder="如 myPets（留空将自动生成）" />
                </div>
              </div>
              <div class="flex flex-col gap-1">
                <FieldLabel label="联动功能开关" name="featureFlag" type="string (flag key)" range="功能开关 key 或留空" example="show_ai_chat" desc="关联功能开关：开关关闭时自动隐藏该导航项。" />
                <NSelect
                  v-model:value="navItem.featureFlag"
                  :options="FLAG_OPTIONS"
                  allow-input
                  clearable
                  size="small"
                  placeholder="联动导航显隐"
                />
              </div>
            </div>
          </div>
        </VueDraggable>

        <NButton size="small" dashed @click="addNavItem">
          <template #icon><SvgIcon icon="mdi:plus" /></template>
          手动添加导航项
        </NButton>

        <div class="rounded border border-dashed border-gray-200 border-solid p-2 text-[11px] leading-relaxed text-gray-400 dark:border-gray-700">
          💡 提示：翻译 key 自动拼接 nav. 前缀；修改「名称」将自动生成唯一后缀并回填 zh/en 翻译；关联 feature flag 后，开关关闭会自动隐藏此导航项。
        </div>
      </div>

      <!-- 4. 分类配置 -->
      <div v-else-if="activeConfigKey === 'categories'" class="flex flex-col gap-3">
        <VueDraggable v-model="config.categories" handle=".cat-drag-handle" :animation="150" class="flex flex-col gap-3">
          <div v-for="(cat, idx) in config.categories" :key="cat.slug || idx" class="rounded border border-gray-200 border-solid p-3 dark:border-gray-700">
            <!-- 第一行：拖拽 + 显隐 + 名称 + 删除 -->
            <div class="mb-2 flex items-center gap-2 border-b border-gray-100 border-solid pb-2 dark:border-gray-700">
              <SvgIcon icon="mdi:drag-vertical" class="cat-drag-handle cursor-grab text-gray-400 hover:text-gray-600" />
              <NSwitch v-model:value="cat.visible" size="small" />
              <NInput
                v-model:value="cat.name"
                size="small"
                placeholder="分类名称"
                style="flex:1"
                @update:value="v => onCategoryNameChanged(idx, v)"
              />
              <NButton size="tiny" quaternary type="error" @click="config.categories.splice(idx, 1)">
                <template #icon><SvgIcon icon="mdi:close" /></template>
              </NButton>
            </div>
            <!-- 第二行：图片/图标 + 字段 -->
            <div class="flex items-start gap-3">
              <div class="flex shrink-0 flex-col items-center gap-1">
                <NUpload v-if="!cat.image" :show-file-list="false" accept="image/*" :custom-request="(opt) => handleImageUpload(opt, { target: 'categoryImage', index: Number(idx) })">
                  <div class="flex h-16 w-16 cursor-pointer items-center justify-center rounded border border-dashed border-gray-300 border-solid text-xs text-gray-400 hover:border-gray-400 dark:border-gray-600">
                    <SvgIcon icon="mdi:upload" />
                  </div>
                </NUpload>
                <div v-else class="relative">
                  <img :src="cat.image" class="h-16 w-16 rounded object-cover" alt="分类图" />
                  <NButton size="tiny" quaternary type="error" class="absolute -right-1 -top-1 !p-0 !h-4 !w-4" @click="cat.image = ''">
                    <template #icon><SvgIcon icon="mdi:close" class="text-10px" /></template>
                  </NButton>
                </div>
                <NInput v-model:value="cat.icon" size="small" placeholder="📦" style="width:56px" class="!text-center" />
              </div>
              <div class="flex min-w-0 flex-1 flex-col gap-2">
                <div class="flex flex-col gap-1">
                  <FieldLabel label="分类图片" name="image" type="image URL" range="http(s):// 或上传" example="https://cdn.example.com/cat-food.png" desc="分类卡片展示图；未上传时可用 Emoji 图标替代。" />
                  <NInput v-model:value="cat.image" size="small" placeholder="分类图 URL（可选）" />
                </div>
                <div class="flex flex-col gap-1">
                  <FieldLabel label="翻译 Key" name="nameKey" type="string (i18n key)" range="点分命名，留空自动生成" example="cat.food" desc="分类名称的 i18n 翻译 key；修改名称时自动生成并回填翻译。" />
                  <NInput v-model:value="cat.nameKey" size="small" placeholder="i18n key（留空将自动生成）" />
                </div>
                <div class="flex flex-col gap-1">
                  <FieldLabel label="路径片段" name="slug" type="string" range="小写字母/数字/中划线" example="cat-food" desc="URL 路径片段，用于分类路由与商品过滤参数。" />
                  <NInput v-model:value="cat.slug" size="small" placeholder="路径片段 slug" />
                </div>
              </div>
            </div>
          </div>
        </VueDraggable>
        <NButton size="small" dashed @click="addCategory">
          <template #icon><SvgIcon icon="mdi:plus" /></template>
          添加分类
        </NButton>
      </div>

      <!-- 5. 页脚链接配置 -->
      <div v-else-if="activeConfigKey === 'footer'" class="flex flex-col gap-4">
        <div class="flex flex-col gap-3">
          <FieldLabel label="版权文案" name="copyright" type="string" range="≤ 200 字符" example="© 2026 Forge. 版权所有。" desc="页脚底部版权文案。" />
          <NInput v-model:value="config.footer.copyright" placeholder="© 2026 Forge. 版权所有。" />
          <div class="flex items-center justify-between">
            <FieldLabel label="邮件订阅" name="newsletter" type="boolean" range="true | false" example="true" desc="是否在页脚显示 Newsletter 订阅输入框。" />
            <NSwitch v-model:value="config.footer.newsletter" />
          </div>
        </div>
        <div class="border-t border-gray-100 border-solid pt-3 dark:border-gray-700" />
        <label class="text-xs font-medium text-gray-500">链接分组</label>
        <NButton size="small" dashed @click="addLinkGroup">
          <template #icon><SvgIcon icon="mdi:plus" /></template>
          添加分组
        </NButton>
        <VueDraggable v-model="config.footer.linkGroups" handle=".group-drag-handle" :animation="150" class="flex flex-col gap-3">
          <div v-for="(group, gIdx) in config.footer.linkGroups" :key="group.key || gIdx" class="rounded border border-gray-200 border-solid p-3 dark:border-gray-700">
            <div class="mb-3 flex items-center gap-2 border-b border-gray-100 border-solid pb-2 dark:border-gray-700">
              <SvgIcon icon="mdi:drag-vertical" class="group-drag-handle cursor-grab text-gray-400 hover:text-gray-600" />
              <NSwitch v-model:value="group.visible" size="small" />
              <NInput
                v-model:value="group.title"
                size="small"
                placeholder="分组标题"
                style="flex:1"
                @update:value="v => onGroupTitleChanged(gIdx, v)"
              />
              <NInput v-model:value="group.titleKey" size="small" placeholder="i18n key（留空自动生成）" style="width:150px" />
              <NButton size="tiny" quaternary type="error" @click="config.footer.linkGroups.splice(gIdx, 1)">
                <template #icon><SvgIcon icon="mdi:close" /></template>
              </NButton>
            </div>
            <div class="flex flex-col gap-2">
              <div v-for="(link, lIdx) in group.links" :key="lIdx" class="rounded border border-gray-100 border-solid p-2 dark:border-gray-700">
                <!-- 第一行：开关 + 链接文字 + 删除 -->
                <div class="mb-1.5 flex items-center gap-2">
                  <NSwitch v-model:value="link.visible" size="small" />
                  <NInput
                    v-model:value="link.label"
                    size="small"
                    placeholder="链接文字"
                    style="flex:1"
                    @update:value="v => onLinkLabelChanged(gIdx, lIdx, v)"
                  />
                  <NButton size="tiny" quaternary type="error" @click="group.links.splice(lIdx, 1)">
                    <template #icon><SvgIcon icon="mdi:close" /></template>
                  </NButton>
                </div>
                <!-- 第二行：i18n key + 跳转路径 -->
                <div class="flex flex-col gap-2">
                  <div class="flex flex-col gap-0.5">
                    <FieldLabel label="翻译 Key" name="labelKey" type="string (i18n key)" range="点分命名，留空自动生成" example="footer.faqs" desc="链接文字的 i18n 翻译 key。" />
                    <NInput v-model:value="link.labelKey" size="small" placeholder="i18n key" />
                  </div>
                  <div class="flex flex-col gap-0.5">
                    <FieldLabel label="跳转路径" name="to" type="string" range="站内路径，/ 开头" example="/faqs" desc="链接点击跳转路径。" />
                    <NInput v-model:value="link.to" size="small" placeholder="/path" />
                  </div>
                </div>
              </div>
              <NButton size="tiny" dashed @click="addLinkToGroup(group)">
                <template #icon><SvgIcon icon="mdi:plus" /></template>
                添加链接
              </NButton>
            </div>
          </div>
        </VueDraggable>
      </div>

      <!-- 6. 首页 Hero / 轮播配置 -->
      <div v-else-if="activeConfigKey === 'homeHero'" class="flex flex-col gap-4">
        <div class="flex items-center justify-between rounded bg-gray-50 p-3 dark:bg-gray-800">
          <FieldLabel label="轮播模式" name="useCarousel" type="boolean" range="true | false" example="false" desc="开启后使用轮播模式（多图自动播放），关闭则为单张 Hero 大图。" />
          <NSwitch v-model:value="config.homeHero.useCarousel" />
        </div>

        <template v-if="!config.homeHero.useCarousel">
          <FieldLabel label="Hero 主标题" name="hero.title" type="string" range="≤ 60 字符" example="Smart Shopping for Your Pet" desc="Hero 大标题文案。" />
          <NInput v-model:value="config.homeHero.hero.title" placeholder="Hero 大标题" />
          <FieldLabel label="主标题翻译 Key" name="hero.titleKey" type="string (i18n key)" range="点分命名" example="home.heroTitle" desc="标题对应的 i18n 翻译 key。" />
          <NInput v-model:value="config.homeHero.hero.titleKey" placeholder="home.heroTitle" />
          <FieldLabel label="Hero 副标题" name="hero.subtitle" type="string" range="≤ 120 字符" example="AI-powered product recommendations..." desc="Hero 副标题描述文案。" />
          <NInput v-model:value="config.homeHero.hero.subtitle" placeholder="描述文字" />
          <FieldLabel label="副标题翻译 Key" name="hero.subtitleKey" type="string (i18n key)" range="点分命名" example="home.heroDesc" desc="副标题对应的 i18n 翻译 key。" />
          <NInput v-model:value="config.homeHero.hero.subtitleKey" placeholder="home.heroDesc" />

          <div class="border-t border-gray-100 border-solid pt-3 dark:border-gray-700" />
          <FieldLabel label="主按钮文字" name="hero.cta1Label" type="string" range="≤ 20 字符" example="Shop Now" desc="主按钮 CTA1 的文字。" />
          <NInput v-model:value="config.homeHero.hero.cta1Label" size="small" placeholder="按钮文字" />
          <FieldLabel label="主按钮翻译 Key" name="hero.cta1LabelKey" type="string (i18n key)" range="点分命名" example="home.shopNow" desc="主按钮 CTA1 文字对应的 i18n 翻译 key。" />
          <NInput v-model:value="config.homeHero.hero.cta1LabelKey" size="small" placeholder="i18n key" />
          <FieldLabel label="主按钮跳转路径" name="hero.cta1To" type="string" range="/ 开头" example="/products" desc="主按钮 CTA1 的跳转路径。" />
          <NInput v-model:value="config.homeHero.hero.cta1To" size="small" placeholder="/path" />
          <FieldLabel label="次按钮文字" name="hero.cta2Label" type="string" range="≤ 20 字符" example="Add Your Pet" desc="次按钮 CTA2 的文字。" />
          <NInput v-model:value="config.homeHero.hero.cta2Label" size="small" placeholder="按钮文字" />
          <FieldLabel label="次按钮翻译 Key" name="hero.cta2LabelKey" type="string (i18n key)" range="点分命名" example="home.addPet" desc="次按钮 CTA2 文字对应的 i18n 翻译 key。" />
          <NInput v-model:value="config.homeHero.hero.cta2LabelKey" size="small" placeholder="i18n key" />
          <FieldLabel label="次按钮跳转路径" name="hero.cta2To" type="string" range="/ 开头" example="/pets" desc="次按钮 CTA2 的跳转路径。" />
          <NInput v-model:value="config.homeHero.hero.cta2To" size="small" placeholder="/path" />

          <div class="border-t border-gray-100 border-solid pt-3 dark:border-gray-700" />
          <FieldLabel label="Hero 背景图" name="hero.backgroundImage" type="image URL" range="http(s):// 或上传" example="https://cdn.example.com/hero.png" desc="Hero 背景图；留空使用默认渐变背景。" />
          <NUpload :show-file-list="false" accept="image/*" :custom-request="(opt) => handleImageUpload(opt, { target: 'heroBg' })">
            <NButton size="small" :loading="uploadingHeroBg">
              <template #icon><SvgIcon icon="mdi:upload" /></template>
              上传背景图
            </NButton>
          </NUpload>
          <div v-if="config.homeHero.hero.backgroundImage" class="relative">
            <img :src="config.homeHero.hero.backgroundImage" class="h-24 w-full rounded object-cover" alt="背景图" />
            <NButton size="tiny" quaternary type="error" class="absolute right-1 top-1" @click="config.homeHero.hero.backgroundImage = ''">
              <template #icon><SvgIcon icon="mdi:close" /></template>
            </NButton>
          </div>
        </template>

        <template v-else>
          <div class="flex flex-col gap-3 rounded bg-gray-50 p-3 dark:bg-gray-800">
            <div class="flex items-center justify-between">
              <FieldLabel label="自动轮播" name="carousel.autoplay" type="boolean" range="true | false" example="true" desc="是否自动轮播。" />
              <NSwitch v-model:value="config.homeHero.carousel.autoplay" size="small" />
            </div>
            <div class="flex flex-col gap-1">
              <FieldLabel label="轮播间隔" name="carousel.interval" type="number (ms)" range="≥ 500，步进 500" example="4000" desc="自动轮播间隔（毫秒）。" />
              <NInputNumber v-model:value="config.homeHero.carousel.interval" :min="500" :step="500" size="small" style="width:120px" />
            </div>
          </div>

          <FieldLabel label="轮播图片列表" name="carousel.images[]" type="array<{url,alt,link,title}>" range="url 必填" example="url: https://.../banner.png" desc="轮播图片列表：每张图可配置标题、Alt 文本与跳转链接。" />
          <VueDraggable v-model="config.homeHero.carousel.images" handle=".carousel-drag-handle" :animation="150" class="flex flex-col gap-3">
            <div v-for="(img, iIdx) in config.homeHero.carousel.images" :key="iIdx" class="rounded border border-gray-200 border-solid p-3 dark:border-gray-700">
              <div class="grid grid-cols-12 gap-2">
                <div class="col-span-1 flex items-center justify-center">
                  <SvgIcon icon="mdi:drag-vertical" class="carousel-drag-handle cursor-grab text-gray-400 hover:text-gray-600" />
                </div>
                <div class="col-span-3">
                  <NUpload v-if="!img.url" :show-file-list="false" accept="image/*" :custom-request="(opt) => handleImageUpload(opt, { target: 'carouselImage', index: Number(iIdx) })">
                    <div class="flex h-20 w-full cursor-pointer items-center justify-center rounded border border-dashed border-gray-300 border-solid text-xs text-gray-400 hover:border-gray-400 dark:border-gray-600">
                      <SvgIcon icon="mdi:upload" />
                    </div>
                  </NUpload>
                  <div v-else class="relative">
                    <img :src="img.url" class="h-20 w-full rounded object-cover" alt="轮播图" />
                    <NUpload :show-file-list="false" accept="image/*" :custom-request="(opt) => handleImageUpload(opt, { target: 'carouselImage', index: Number(iIdx) })">
                      <div class="absolute inset-0 flex cursor-pointer items-center justify-center rounded bg-black/30 opacity-0 transition-opacity hover:opacity-100">
                        <span class="text-xs text-white">重新上传</span>
                      </div>
                    </NUpload>
                  </div>
                </div>
                <div class="col-span-7 flex flex-col gap-2">
                  <FieldLabel label="图片标题" name="title" type="string" range="≤ 40 字符" example="夏日促销" desc="轮播图标题（部分主题展示在图片上）。" />
                  <NInput v-model:value="img.title" size="small" placeholder="标题" />
                  <FieldLabel label="Alt 文本" name="alt" type="string" range="≤ 100 字符" example="宠物食品促销横幅" desc="图片 Alt 文本，用于无障碍与 SEO。" />
                  <NInput v-model:value="img.alt" size="small" placeholder="Alt 文本" />
                  <FieldLabel label="跳转链接" name="link" type="string" range="站内路径 / 开头" example="/products" desc="点击轮播图跳转路径。" />
                  <NInput v-model:value="img.link" size="small" placeholder="跳转链接（如 /products）" />
                </div>
                <div class="col-span-1 flex items-start justify-end">
                  <NButton size="tiny" quaternary type="error" @click="config.homeHero.carousel.images.splice(iIdx, 1)">
                    <template #icon><SvgIcon icon="mdi:close" /></template>
                  </NButton>
                </div>
              </div>
            </div>
          </VueDraggable>

          <NUpload :show-file-list="false" accept="image/*" :custom-request="(opt) => handleImageUpload(opt, { target: 'carouselImageNew' })">
            <NButton size="small" dashed style="width:100%">
              <template #icon><SvgIcon icon="mdi:plus" /></template>
              添加轮播图片
            </NButton>
          </NUpload>
        </template>
      </div>

      <!-- 7. SEO 配置 -->
      <div v-else-if="activeConfigKey === 'seo'" class="flex flex-col gap-3">
        <FieldLabel label="标题模板" name="seo.titleTemplate" type="string" range="含 %s 占位符，≤ 80 字符" example="%s | Forge" desc="页面标题模板：%s 会被替换为当前页面标题。" />
        <NInput v-model:value="config.seo.titleTemplate" placeholder="%s | Forge" />
        <FieldLabel label="首页标题" name="seo.homeTitle" type="string" range="≤ 60 字符" example="Forge 宠物商城 - AI 驱动" desc="首页浏览器标题。" />
        <NInput v-model:value="config.seo.homeTitle" placeholder="首页 SEO 标题" />
        <FieldLabel label="页面描述" name="seo.description" type="string" range="≤ 150 字符" example="AI 驱动的宠物用品商城" desc="首页 Meta 描述，展示在搜索结果摘要。" />
        <NInput v-model:value="config.seo.description" type="textarea" placeholder="页面描述（150字以内）" :rows="4" />
        <FieldLabel label="关键词" name="seo.metaKeywords" type="string" range="英文逗号分隔，≤ 20 个" example="宠物,宠物食品,AI商城" desc="首页 Meta 关键词。" />
        <NInput v-model:value="config.seo.metaKeywords" placeholder="关键词, 用逗号分隔" />
      </div>

      <!-- 8. i18n 多语言配置 -->
      <div v-else-if="activeConfigKey === 'i18n'" class="flex flex-col gap-4">
        <FieldLabel label="默认语言" name="i18n.defaultLocale" type="enum" range="见下拉选项" example="zh-CN" desc="站点默认语言；未启用语言中不可选。" />
        <NSelect v-model:value="config.i18n.defaultLocale" :options="localeOptions" size="small" />
        <FieldLabel label="启用语言" name="i18n.locales[]" type="array<enum>" range="至少 1 个" example="['zh-CN','en-US']" desc="启用的语言列表；切换 Tab 编辑各语言翻译。" />
        <NSelect v-model:value="config.i18n.locales" :options="localeOptions" multiple size="small" />

        <div class="border-t border-gray-100 border-solid pt-3 dark:border-gray-700" />
        <label class="text-xs font-medium text-gray-500">翻译编辑器</label>

        <template v-if="config.i18n.locales.length === 0">
          <div class="rounded border border-dashed border-gray-200 border-solid p-6 text-center text-sm text-gray-400 dark:border-gray-700">
            请先在上方选择启用语言
          </div>
        </template>
        <template v-else>
          <NTabs v-model:value="activeLocale" type="segment" size="small" class="mb-2">
            <NTabPane v-for="opt in localeTabsOptions" :key="opt.value" :name="opt.value" :tab="opt.label" />
          </NTabs>

          <div class="max-h-64 overflow-y-auto rounded border border-gray-200 border-solid dark:border-gray-700">
            <table class="w-full text-sm">
              <thead class="sticky top-0 bg-gray-50 dark:bg-gray-800">
                <tr class="text-left text-xs text-gray-500">
                  <th class="w-1/2 border-b border-gray-100 border-solid p-2 dark:border-gray-700">Key</th>
                  <th class="w-1/2 border-b border-gray-100 border-solid p-2 dark:border-gray-700">翻译 Value</th>
                  <th class="w-10 border-b border-gray-100 border-solid p-2 dark:border-gray-700"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in translationEntries" :key="entry._idx" class="border-b border-gray-100 border-solid last:border-0 dark:border-gray-700">
                  <td class="p-1">
                    <NInput :value="entry.k" @update:value="v => updateTranslationKey(entry._idx, v)" size="tiny" class="font-mono" />
                  </td>
                  <td class="p-1">
                    <NInput :value="entry.v" @update:value="v => updateTranslationVal(entry._idx, v)" size="tiny" />
                  </td>
                  <td class="p-1 text-right">
                    <NButton size="tiny" quaternary type="error" @click="removeTranslation(entry.k)">
                      <template #icon><SvgIcon icon="mdi:close" /></template>
                    </NButton>
                  </td>
                </tr>
                <tr v-if="Object.keys(currentTranslations).length === 0">
                  <td colspan="3" class="p-4 text-center text-xs text-gray-400">暂无翻译条目，使用下方添加</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex items-center gap-2">
            <NInput v-model:value="newKey" size="small" placeholder="新的 key (如 nav.home)" style="flex:1" />
            <NInput v-model:value="newValue" size="small" placeholder="翻译值" style="flex:1" />
            <NButton size="small" type="primary" @click="addTranslation">添加</NButton>
          </div>
        </template>
      </div>

      <!-- 9. 功能开关 -->
      <div v-else-if="activeConfigKey === 'featureFlags'" class="flex flex-col gap-2">
        <FieldLabel label="内置功能开关" name="featureFlags.<key>" type="boolean" range="true | false" example="show_ai_chat: true" desc="内置功能开关；关闭后对应功能在前台隐藏。导航项可通过 featureFlag 关联联动显隐。" />
        <div v-for="(label, key) in FLAG_LABELS" :key="key" class="flex items-center justify-between rounded border border-gray-100 border-solid p-2 dark:border-gray-700">
          <span class="text-sm">{{ label }}</span>
          <NSwitch v-model:value="config.featureFlags[key]" />
        </div>
        <FieldLabel label="自定义功能开关" name="featureFlags.<自定义key>" type="boolean" range="小写字母/数字/下划线" example="enable_loyalty" desc="自定义功能开关；输入 key 后添加，供前台按 key 判断。" />
        <div v-for="(val, key) in customFlags" :key="key" class="flex items-center justify-between rounded border border-gray-100 border-solid p-2 dark:border-gray-700">
          <span class="text-sm font-mono text-xs">{{ key }}</span>
          <div class="flex items-center gap-2">
            <NSwitch v-model:value="config.featureFlags[key]" />
            <NButton size="tiny" quaternary type="error" @click="deleteCustomFlag(key)">
              <template #icon><SvgIcon icon="mdi:close" /></template>
            </NButton>
          </div>
        </div>
        <div class="flex items-center gap-2 pt-2">
          <NInput v-model:value="newFlagKey" size="small" placeholder="自定义开关 key (如 enable_xxx)" style="flex:1" />
          <NButton size="small" @click="addFlag">添加</NButton>
        </div>
      </div>

      <!-- 10. 货币配置 -->
      <div v-else-if="activeConfigKey === 'currencies'" class="flex flex-col gap-2">
        <FieldLabel label="结算货币" name="currencies[]" type="array<string (ISO 4217)>" range="3 位大写字母代码" example="['CNY','USD']" desc="启用的结算货币列表；第一个为默认展示货币。" />
        <div v-for="(cur, idx) in config.currencies" :key="idx" class="flex items-center gap-2">
          <NInput v-model:value="config.currencies[idx]" size="small" placeholder="货币代码 (如 USD, CNY, EUR)" style="flex:1" />
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

    <div v-else class="flex h-full flex-col items-center justify-center gap-3 text-gray-400">
      <SvgIcon icon="mdi:cog-outline" class="text-48px" />
      <span class="text-sm">请从左侧选择一个配置项</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import {
  NButton,
  NColorPicker,
  NInput,
  NInputNumber,
  NSelect,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  NUpload,
  type UploadCustomRequestOptions
} from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { useDiyStore, SITE_CONFIG_ITEMS, THEME_PRESETS } from '@/store/modules/diy';
import type { SelectedElementInfo } from '@/store/modules/diy';
import { siteApi } from '@/service/api/diy';
import FieldLabel from './FieldLabel.vue';

const store = useDiyStore();

const activeConfigKey = computed(() => store.activeSiteConfigItem);

const selectedElement = computed<SelectedElementInfo | null>(() => store.selectedElement);

function clearSelectedElement() {
  store.setSelectedElement(null);
}

const configLabel = computed(() => {
  const item = SITE_CONFIG_ITEMS.find(i => i.key === activeConfigKey.value);
  return item?.label || '';
});

const config = computed(() => store.siteConfig);

/**
 * 简易 SVG sanitize：过滤 <script> / <iframe> / <object> / <embed> / 内联事件 onxxx= / javascript: 协议，
 * 防止 v-html 注入。生产级可替换为 dompurify，这里轻量覆盖常见攻击向量。
 */
function sanitizeSvg(input: string): string {
  if (!input) return '';
  let s = input;
  // 1) 移除危险标签（含内部内容，非贪婪）
  s = s.replace(/<\s*(script|iframe|object|embed|form|input|button|a)\b[\s\S]*?<\/\s*\1\s*>/gi, '');
  s = s.replace(/<\s*(script|iframe|object|embed|form|input|button|a)\b[^>]*(\/)?>/gi, '');
  // 2) 移除 XML 外部实体解析 / DOCTYPE 注入
  s = s.replace(/<!DOCTYPE[\s\S]*?>/gi, '');
  s = s.replace(/<!\[CDATA\[[\s\S]*?\]\]>/g, '');
  s = s.replace(/<\?[\s\S]*?\?>/g, '');
  // 3) 移除所有 onxxx= 事件处理
  s = s.replace(/\son[a-z]+\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))/gi, '');
  // 4) 移除 href / src 等属性中的 javascript: / data:text/html 协议
  s = s.replace(/(\s(?:href|src|srcdoc|xlink:href|action|style)\s*=\s*)("([^"]*)"|'([^']*)')/gi, (match, attr, quoted) => {
    const inner = quoted.slice(1, -1).trim();
    if (/^(javascript|vbscript|data:text)/i.test(inner.replace(/\s+/g, ''))) return '';
    return match;
  });
  // 5) 禁止 style 内的 expression / url(javascript:)
  s = s.replace(/(\sstyle\s*=\s*)("([^"]*)"|'([^']*)')/gi, (_, attr, quoted) => {
    const raw = quoted.slice(1, -1);
    const cleaned = raw
      .replace(/expression\s*\(/gi, '')
      .replace(/url\s*\(\s*['"]?\s*javascript:/gi, 'url("');
    return `${attr}"${cleaned}"`;
  });
  return s;
}

/** 品牌 SVG 代码的实时预览（经过 sanitize） */
const brandSvgPreview = computed(() => {
  if (config.value.brand?.logo?.type !== 'svg') return '';
  return sanitizeSvg(config.value.brand?.logo?.data || '');
});

const saving = ref(false);

const uploadingBrandLogo = ref(false);
const uploadingHeroBg = ref(false);
const uploadingCategoryImages = reactive<Record<number, boolean>>({});
const uploadingCarouselImages = reactive<Record<number, boolean>>({});

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

const localeTabsOptions = computed(() => {
  const locales = config.value.i18n?.locales || [];
  return locales
    .filter(Boolean)
    .map((locale: string) => {
      const found = localeOptions.find(opt => opt.value === locale);
      return { label: found?.label || locale, value: locale };
    });
});

const FLAG_LABELS: Record<string, string> = {
  show_pets_page: '宠物页面',
  show_ai_chat: 'AI客服聊天',
  show_categories_section: '分类展示区',
  show_featured_products: '精选商品区',
  show_tailored_pets: '宠物定制推荐区',
  show_ai_teaser: 'AI推荐引导横幅',
  show_newsletter: '底部订阅邮件',
  enable_reviews: '商品评价',
  enable_wishlist: '心愿单',
  enable_live_chat: '在线客服浮窗'
};

/** 导航配置 - 快捷预设 */
const NAV_PRESETS: Array<{ label: string; to: string; featureFlag?: string }> = [
  { label: '🏠 首页', to: '/' },
  { label: '🛍 商品', to: '/products' },
  { label: '🐾 宠物', to: '/pets', featureFlag: 'show_pets_page' },
  { label: '📦 订单', to: '/orders' },
  { label: '💬 AI客服', to: '/chat', featureFlag: 'show_ai_chat' },
  { label: '👤 登录', to: '/login' },
  { label: '📝 注册', to: '/register' },
  { label: '📖 博客', to: '/blog' }
];

/** 导航路径下拉选项（常用路径） */
const PATH_OPTIONS = NAV_PRESETS.map(p => ({ label: `${p.label}  →  ${p.to}`, value: p.to })).concat([
  { label: '/cart 购物车', value: '/cart' },
  { label: '/checkout 结算', value: '/checkout' },
  { label: '/faq 常见问题', value: '/faqs' },
  { label: '/contact 联系我们', value: '/contact' },
  { label: '/about 关于我们', value: '/story' },
  { label: '/shipping 配送', value: '/shipping' },
  { label: '/returns 退换货', value: '/returns' },
  { label: '/privacy 隐私政策', value: '/privacy' },
  { label: '/terms 服务条款', value: '/terms' }
]);

/** feature flag 下拉选项 */
const FLAG_OPTIONS = Object.entries(FLAG_LABELS).map(([value, label]) => ({
  label: `${value} (${label})`,
  value
}));

/**
 * ============ 自动 i18n 工具函数 ============
 *  - slugify：把中文/英文标签转成 camelCase key 片段
 *  - ensureAllLocalesReady：确保启用的 locales 都有 translations 表（默认 zh/en 至少存在）
 *  - writeTranslation：写某个 locale 的翻译（写入所有启用的 locale，中文 locale 用原文，英文 locale 简单占位或用简单原文）
 *  - bindLabelToI18n：用户改 label 时，若 labelKey 为空则生成并回填，同时写入翻译表
 */

const ZH_RE = /[\u4e00-\u9fa5]/;

/**
 * 轻量转 key：
 *  - 含中文 → 拼音风格（无法拼音就用 nav.item${n} 递增 fallback，这里简单用 hash-free index）
 *  - 英文 → camelCase
 *  - 返回结果保证唯一性（在现有 translations keys + 已有 labelKeys 中查重）
 */
function slugifyPart(input: string): string {
  const s = (input || '').trim();
  if (!s) return 'item';
  if (ZH_RE.test(s)) {
    // 中文：简单 fallback：每个字 -> 'zh'，实际项目可替换为 pinyin-pro，这里用简短 hash
    return 'zh_' + Array.from(s).slice(0, 4).map(ch => ch.charCodeAt(0).toString(36)).join('');
  }
  // 英文/数字：word 分隔 → camelCase
  const words = s.split(/[^A-Za-z0-9]+/).filter(Boolean);
  if (words.length === 0) return 'item';
  const first = words[0].toLowerCase();
  const rest = words.slice(1).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
  return (first + rest.join('')).replace(/^[0-9]+/, '');
}

function usedI18nKeys(): Set<string> {
  const set = new Set<string>();
  if (config.value.i18n?.translations) {
    for (const locale of Object.keys(config.value.i18n.translations)) {
      Object.keys(config.value.i18n.translations[locale]).forEach(k => set.add(k));
    }
  }
  (config.value.navigation || []).forEach((n: any) => n.labelKey && set.add(n.labelKey));
  (config.value.categories || []).forEach((c: any) => c.nameKey && set.add(c.nameKey));
  (config.value.footer?.linkGroups || []).forEach((g: any) => {
    if (g.titleKey) set.add(g.titleKey);
    (g.links || []).forEach((l: any) => l.labelKey && set.add(l.labelKey));
  });
  return set;
}

function ensureAllLocalesReady() {
  if (!config.value.i18n) return;
  if (!config.value.i18n.locales || config.value.i18n.locales.length === 0) {
    config.value.i18n.locales = ['zh', 'en'];
  }
  if (!config.value.i18n.defaultLocale) {
    config.value.i18n.defaultLocale = config.value.i18n.locales[0];
  }
  if (!config.value.i18n.translations) config.value.i18n.translations = {};
  for (const locale of config.value.i18n.locales) {
    if (!config.value.i18n.translations[locale]) {
      config.value.i18n.translations[locale] = {};
    }
  }
}

/**
 * 生成唯一 i18n key 并写入 translations 表（所有启用 locale）
 * @param prefix 命名空间，如 'nav' / 'cat' / 'footer' / 'footer.link'
 * @param value 用户输入的原始标签文本
 */
function generateLabelKeyAndWrite(prefix: string, value: string): string {
  ensureAllLocalesReady();
  const used = usedI18nKeys();
  const base = slugifyPart(value) || 'item';
  let key = `${prefix}.${base}`;
  let i = 2;
  while (used.has(key)) {
    key = `${prefix}.${base}${i}`;
    i += 1;
  }
  // 写入所有启用 locale
  const locales = config.value.i18n!.locales as string[];
  for (const locale of locales) {
    ensureTranslationsForLocale(locale);
    // 中文 locale：写入用户原文；英文 locale：如用户写英文就用原文，否则先用占位 + 中文原文
    if (locale.startsWith('zh') || ZH_RE.test(value) === false) {
      config.value.i18n!.translations![locale][key] = value;
    } else {
      config.value.i18n!.translations![locale][key] = value; // 占位，用户可后续在翻译面板精修
    }
  }
  return key;
}

/**
 * 手动修改 i18n key 时，把旧 key 下已有的所有 locale 翻译值迁移到新 key，
 * 若旧 key 不存在值则回写 fallbackValue 到新 key（防止 labelKey 与 translations 字典 key 脱节）。
 */
function renameTranslationKey(oldKey: string, newKey: string, fallbackValue?: string) {
  const from = (oldKey || '').trim();
  const to = (newKey || '').trim();
  if (!to || from === to) return;
  ensureAllLocalesReady();
  const locales = config.value.i18n!.locales as string[];
  for (const locale of locales) {
    ensureTranslationsForLocale(locale);
    const dict = config.value.i18n!.translations![locale];
    if (from && Object.prototype.hasOwnProperty.call(dict, from)) {
      dict[to] = dict[from];
      delete dict[from];
    } else if (fallbackValue !== undefined && fallbackValue !== null && `${fallbackValue}`.length > 0) {
      if (!Object.prototype.hasOwnProperty.call(dict, to)) {
        dict[to] = `${fallbackValue}`;
      }
    }
  }
}

/** ============ i18n key 手动变更回调（迁移旧 key → 新 key，避免 translations 错位） ============ */

function onNavLabelKeyChanged(idx: number | string, oldKey: string, v: string | number) {
  const i = Number(idx);
  const item: any = config.value.navigation?.[i];
  if (!item) return;
  // 自动剥离并拼接 nav. 公共前缀：输入框只填后缀，存储为完整 key（兼容粘贴完整 key 的场景）
  const raw = String(v ?? '').trim();
  let suffix = raw.startsWith('nav.') ? raw.slice(4) : raw;
  suffix = suffix.replace(/^\.+/, '');
  const newKey = suffix ? `nav.${suffix}` : '';
  item.labelKey = newKey;
  renameTranslationKey(oldKey, newKey, item.label);
}

/** 导航 labelKey 显示为去前缀后的后缀（输入框只展示/编辑 nav. 之后的部分） */
function navKeySuffix(key: string): string {
  const k = (key || '').trim();
  return k.startsWith('nav.') ? k.slice(4) : k;
}

function onCategoryNameKeyChanged(idx: number | string, oldKey: string, v: string | number) {
  const i = Number(idx);
  const newKey = String(v ?? '').trim();
  const cat: any = config.value.categories?.[i];
  if (!cat) return;
  cat.nameKey = newKey;
  renameTranslationKey(oldKey, newKey, cat.name);
}

function onGroupTitleKeyChanged(gIdx: number | string, oldKey: string, v: string | number) {
  const gi = Number(gIdx);
  const newKey = String(v ?? '').trim();
  const group: any = config.value.footer?.linkGroups?.[gi];
  if (!group) return;
  group.titleKey = newKey;
  renameTranslationKey(oldKey, newKey, group.title);
}

function onLinkLabelKeyChanged(gIdx: number | string, lIdx: number | string, oldKey: string, v: string | number) {
  const gi = Number(gIdx);
  const li = Number(lIdx);
  const newKey = String(v ?? '').trim();
  const link: any = config.value.footer?.linkGroups?.[gi]?.links?.[li];
  if (!link) return;
  link.labelKey = newKey;
  renameTranslationKey(oldKey, newKey, link.label);
}

function onHeroTextKeyChanged(field: 'titleKey' | 'subtitleKey' | 'cta1LabelKey' | 'cta2LabelKey', oldKey: string, v: string | number) {
  const newKey = String(v ?? '').trim();
  const hero: any = config.value.homeHero?.hero;
  if (!hero) return;
  hero[field] = newKey;
  const fallbackField = field === 'titleKey' ? 'title' : field === 'subtitleKey' ? 'subtitle' : (field === 'cta1LabelKey' ? 'cta1Label' : 'cta2Label');
  renameTranslationKey(oldKey, newKey, hero[fallbackField]);
}

/** ============ 各模块 label 变更回调 ============ */

function onNavLabelChanged(idx: number | string, v: string | number) {
  const i = Number(idx);
  const value = String(v ?? '');
  const item: any = config.value.navigation?.[i];
  if (!item || !value) return;
  if (!item.labelKey) {
    item.labelKey = generateLabelKeyAndWrite('nav', value);
  } else {
    // 已有 key：更新各 locale 中的 value（保持 key 不变）
    ensureAllLocalesReady();
    const locales = config.value.i18n!.locales as string[];
    for (const locale of locales) {
      ensureTranslationsForLocale(locale);
      config.value.i18n!.translations![locale][item.labelKey] = value;
    }
  }
}

function onCategoryNameChanged(idx: number | string, v: string | number) {
  const i = Number(idx);
  const value = String(v ?? '');
  const cat: any = config.value.categories?.[i];
  if (!cat || !value) return;
  if (!cat.nameKey) {
    cat.nameKey = generateLabelKeyAndWrite('cat', value);
    // 顺便生成 slug（name 若英文直接 slugify，中文使用 nameKey 后缀）
    if (!cat.slug) {
      const base = (ZH_RE.test(value)
        ? slugifyPart(value)
        : value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''));
      cat.slug = base || `cat-${Date.now()}`;
    }
  } else {
    ensureAllLocalesReady();
    const locales = config.value.i18n!.locales as string[];
    for (const locale of locales) {
      ensureTranslationsForLocale(locale);
      config.value.i18n!.translations![locale][cat.nameKey] = value;
    }
  }
}

function onGroupTitleChanged(gIdx: number | string, v: string | number) {
  const gi = Number(gIdx);
  const value = String(v ?? '');
  const group: any = config.value.footer?.linkGroups?.[gi];
  if (!group || !value) return;
  if (!group.titleKey) {
    group.titleKey = generateLabelKeyAndWrite('footer', value);
  } else {
    ensureAllLocalesReady();
    const locales = config.value.i18n!.locales as string[];
    for (const locale of locales) {
      ensureTranslationsForLocale(locale);
      config.value.i18n!.translations![locale][group.titleKey] = value;
    }
  }
}

function onLinkLabelChanged(gIdx: number | string, lIdx: number | string, v: string | number) {
  const gi = Number(gIdx);
  const li = Number(lIdx);
  const value = String(v ?? '');
  const link: any = config.value.footer?.linkGroups?.[gi]?.links?.[li];
  if (!link || !value) return;
  if (!link.labelKey) {
    link.labelKey = generateLabelKeyAndWrite('footer.link', value);
  } else {
    ensureAllLocalesReady();
    const locales = config.value.i18n!.locales as string[];
    for (const locale of locales) {
      ensureTranslationsForLocale(locale);
      config.value.i18n!.translations![locale][link.labelKey] = value;
    }
  }
}

const customFlags = computed(() => {
  const result: Record<string, boolean> = {};
  if (!config.value.featureFlags) return result;
  for (const k of Object.keys(config.value.featureFlags)) {
    if (!(k in FLAG_LABELS)) {
      result[k] = config.value.featureFlags[k];
    }
  }
  return result;
});

const newFlagKey = ref('');

function addFlag() {
  const k = newFlagKey.value.trim();
  if (k && config.value.featureFlags) {
    config.value.featureFlags[k] = false;
    newFlagKey.value = '';
  }
}

function deleteCustomFlag(key: string) {
  if (config.value.featureFlags) {
    delete config.value.featureFlags[key];
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

function extractUrl(res: any): string {
  return res?.data?.data?.url || res?.data?.url || res?.url || '';
}

type UploadTarget =
  | { target: 'brandLogo' }
  | { target: 'heroBg' }
  | { target: 'categoryImage'; index: number }
  | { target: 'carouselImage'; index: number }
  | { target: 'carouselImageNew' };

async function handleImageUpload(
  { file, onFinish, onError }: UploadCustomRequestOptions,
  opts: UploadTarget
) {
  const setLoading = (v: boolean) => {
    switch (opts.target) {
      case 'brandLogo': uploadingBrandLogo.value = v; break;
      case 'heroBg': uploadingHeroBg.value = v; break;
      case 'categoryImage': uploadingCategoryImages[opts.index] = v; break;
      case 'carouselImage': uploadingCarouselImages[opts.index] = v; break;
    }
  };
  setLoading(true);
  try {
    const res = await siteApi.uploadImage(file.file as File);
    const url = extractUrl(res);
    if (!url) throw new Error('no url');
    switch (opts.target) {
      case 'brandLogo':
        config.value.brand.logo.data = url;
        break;
      case 'heroBg':
        config.value.homeHero.hero.backgroundImage = url;
        break;
      case 'categoryImage':
        if (config.value.categories[opts.index]) {
          config.value.categories[opts.index].image = url;
        }
        break;
      case 'carouselImage':
        if (config.value.homeHero.carousel.images[opts.index]) {
          config.value.homeHero.carousel.images[opts.index].url = url;
        }
        break;
      case 'carouselImageNew':
        config.value.homeHero.carousel.images.push({
          url, alt: '', link: '', title: ''
        });
        break;
    }
    onFinish?.();
  } catch (e) {
    window.$message?.error('上传失败');
    onError?.();
  } finally {
    setLoading(false);
  }
}

function applyThemePreset(presetKey: string) {
  const preset = THEME_PRESETS[presetKey];
  if (!preset || !preset.colors) return;
  const colors = preset.colors as any;
  for (const k of Object.keys(colors)) {
    if (k in config.value.theme) {
      config.value.theme[k] = colors[k];
    }
  }
}

function addNavItem() {
  const item: any = {
    key: `nav_${Date.now()}`,
    to: '/',
    label: '新导航',
    labelKey: '',
    visible: true,
    order: 0,
    _open: true
  };
  config.value.navigation.push(item);
  // 自动生成 i18n labelKey + 翻译
  item.labelKey = generateLabelKeyAndWrite('nav', item.label);
}

/** 导航快捷预设：一键添加并绑定 feature flag 联动 */
function addNavPreset(preset: { label: string; to: string; featureFlag?: string }) {
  // 若已有 to 相同的导航项，不再重复添加（避免重复）
  const exists = (config.value.navigation || []).some((n: any) => n.to === preset.to);
  if (exists) {
    window.$message?.warning(`已存在跳转路径为 ${preset.to} 的导航项`);
    return;
  }
  const item: any = {
    key: `nav_${Date.now()}`,
    to: preset.to,
    label: preset.label.replace(/^[^\u4e00-\u9fa5A-Za-z]+/, '').trim() || preset.label,
    labelKey: '',
    visible: true,
    order: 0,
    featureFlag: preset.featureFlag || '',
    _open: true
  };
  config.value.navigation.push(item);
  item.labelKey = generateLabelKeyAndWrite('nav', item.label);
  // 若绑定了 feature flag 且当前 flag=false，则初始置为不可见（自动同步）
  if (item.featureFlag && config.value.featureFlags && config.value.featureFlags[item.featureFlag] === false) {
    item.visible = false;
  }
}

/**
 * 导航 feature flag 联动监听器
 *  - 当 feature flag X 关闭时：所有 featureFlag === X 的导航项 visible=false
 *  - 当 feature flag X 打开时：还原 visible=true（仅针对那些因 flag 被关闭的项，这里简单恢复）
 */
watch(
  () => config.value.featureFlags,
  (flags) => {
    if (!flags || !config.value.navigation) return;
    for (const navItem of config.value.navigation as any[]) {
      if (!navItem.featureFlag) continue;
      const flagVal = flags[navItem.featureFlag];
      if (flagVal === false) {
        navItem.visible = false;
      } else if (flagVal === true && !navItem.visible) {
        // flag 打开 → 若导航之前因 flag 而不可见，则恢复可见（保留用户手动操作的简单策略）
        navItem.visible = true;
      }
    }
  },
  { deep: true }
);

function addCategory() {
  const cat: any = {
    slug: '',
    name: '新分类',
    nameKey: '',
    icon: '📦',
    image: '',
    visible: true,
    order: 0
  };
  config.value.categories.push(cat);
  cat.nameKey = generateLabelKeyAndWrite('cat', cat.name);
  cat.slug = `cat-${Date.now()}`;
}

function addLinkGroup() {
  const group: any = {
    key: `g_${Date.now()}`,
    title: '新分组',
    titleKey: '',
    visible: true,
    order: 0,
    links: []
  };
  config.value.footer.linkGroups.push(group);
  group.titleKey = generateLabelKeyAndWrite('footer', group.title);
}

function addLinkToGroup(group: any) {
  const link: any = {
    label: '新链接',
    labelKey: '',
    to: '/',
    visible: true
  };
  group.links.push(link);
  link.labelKey = generateLabelKeyAndWrite('footer.link', link.label);
}

const activeLocale = ref<string>('en');

watch(() => config.value.i18n?.defaultLocale, (v) => {
  if (v && !config.value.i18n?.locales?.includes(v)) {
    // skip
  }
  if (v && config.value.i18n?.locales?.length) {
    activeLocale.value = v;
  }
}, { immediate: true });

watch(() => config.value.i18n?.locales?.[0], (v) => {
  if (v && !activeLocale.value) activeLocale.value = v;
  if (v && !config.value.i18n?.locales?.includes(activeLocale.value)) {
    activeLocale.value = v;
  }
});

function ensureTranslationsForLocale(locale: string) {
  if (!config.value.i18n.translations) {
    config.value.i18n.translations = {};
  }
  if (!config.value.i18n.translations[locale]) {
    config.value.i18n.translations[locale] = {};
  }
}

const currentTranslations = computed({
  get(): Record<string, string> {
    const locale = activeLocale.value;
    ensureTranslationsForLocale(locale);
    return config.value.i18n.translations[locale];
  },
  set() {}
});

const translationEntries = computed<Array<{ _idx: number; k: string; v: string }>>(() => {
  return Object.entries(currentTranslations.value).map(([k, v], idx) => ({ _idx: idx, k, v }));
});

function updateTranslationKey(idx: number, newKey: string) {
  const locale = activeLocale.value;
  ensureTranslationsForLocale(locale);
  const entries = Object.entries(config.value.i18n.translations[locale]);
  const target = entries[idx];
  if (!target) return;
  const [oldKey, oldVal] = target;
  if (oldKey === newKey) return;
  delete config.value.i18n.translations[locale][oldKey];
  config.value.i18n.translations[locale][newKey] = oldVal;
}

function updateTranslationVal(idx: number, newVal: string) {
  const locale = activeLocale.value;
  ensureTranslationsForLocale(locale);
  const entries = Object.entries(config.value.i18n.translations[locale]);
  const target = entries[idx];
  if (!target) return;
  const [k] = target;
  config.value.i18n.translations[locale][k] = newVal;
}

const newKey = ref('');
const newValue = ref('');

function addTranslation() {
  const k = newKey.value.trim();
  const v = newValue.value;
  if (!k) return;
  const locale = activeLocale.value;
  ensureTranslationsForLocale(locale);
  config.value.i18n.translations[locale][k] = v;
  newKey.value = '';
  newValue.value = '';
}

function removeTranslation(k: string) {
  const locale = activeLocale.value;
  if (config.value.i18n?.translations?.[locale]) {
    delete config.value.i18n.translations[locale][k];
  }
}
</script>
