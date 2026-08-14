# C 端多语言（i18n）规划：切换机制与配置规范

> 适用范围：Forge portal-web（Nuxt C 端）+ admin 站点配置（site-config）。
> 更新日期：2026-08-14。

---

## 1. 现状与目标

- C 端界面文案（vue-i18n 静态语言包）：`app/i18n/locales/{en,zh,ar,de,fr}.json`，由 `nuxt.config` i18n 模块管理，`strategy: 'prefix'`（`/de/xxx` 带语言前缀路由），`defaultLocale: 'en'`，`ar` 已配 `dir: 'rtl'`。
- 站点动态文案（后台可编辑）：`DEFAULT_SITE_CONFIG.i18n` 由 admin 站点配置面板管理，含 `locales` 列表与 `translations` 字典（当前预置 en/zh/ar/de/fr 五语言，key 分 `nav.` / `cat.` / `footer.` 三个命名空间）。
- 目标：**任意语言可平滑扩展**。新增语言只需两步（见 §4），前端语言切换下拉由站点配置驱动，不写死。

## 2. 运行时切换机制

### 2.1 三层文案来源与合并顺序（优先级从高到低）

1. **站点配置 translations**（admin 后台 i18n 面板按语言 Tab 编辑）：`nav.* / cat.* / footer.* / home.*` 等站点动态文案。
2. **C 端静态语言包**（`app/i18n/locales/*.json`）：页面固定 UI 文案（按钮、表单、导航通用词等）。
3. **fallback**（`i18n.config.ts`）：`fallbackLocale: 'en'`，缺失 key 回退英文，`missingWarn/fallbackWarn` 关闭避免控制台刷屏。

> 合并实现：`useSiteProfile.applyI18nTranslations` 将站点 `translations[locale]` 按命名空间合并进 vue-i18n 运行时；C 端组件统一用 `useI18n().t(key)` 取文案。

### 2.2 语言切换入口

- **桌面端 / 移动端**：`AppHeader.vue` 语言下拉，选项由 `enabledLocaleOptions` 计算属性驱动（`profile.i18n.locales` 过滤出已启用语言），不再硬编码。
- 切换动作：`setLocale(code)` → vue-i18n 切换 → URL 前缀路由变化（`/de/...`）。
- RTL：`ar` 自动启用 RTL（nuxt.config i18n `dir` 字段），页面布局自适应。

## 3. key 命名空间规范（后台配置）

| 命名空间 | 用途 | 示例 | 后台 UI |
|---|---|---|---|
| `nav.` | 顶部导航项 | `nav.products` | 导航区块「翻译 Key 后缀」输入框，自动拼 `nav.` 前缀 |
| `cat.` | 商品分类 | `cat.food` | 分类区块「翻译 Key 后缀」，自动拼 `cat.` 前缀 |
| `footer.` | 页脚分组/链接 | `footer.support` / `footer.faqs` | 页脚区块「翻译 Key 后缀」，自动拼 `footer.` 前缀 |
| `home.` | 首页轮播/CTA | `home.heroTitle` | homeHero 区块直接编辑完整 key |

规则：
- 输入框只填**后缀**（如 `faqs`），保存/失焦时自动拼接前缀，兼容粘贴完整 key。
- 历史数据兜底：`saveSiteConfig` 自动把漏前缀 / `footer.` 开头的分类 key 归一为 `cat.`，把导航 key 归一为 `nav.`。
- 同一语言下 key 必须唯一，改名时旧 key 的翻译值自动迁移（`renameTranslationKey`）。

## 4. 新增一种语言（两步）

以新增日语 `ja` 为例：

1. **admin 站点配置**：
   - i18n 面板 `locales` 勾选 `ja`（localeOptions 已内置 ja 标签）；
   - 切到 `ja` Tab，为 `nav.* / cat.* / footer.*` 补齐日语文案（漏项回退英文）。
2. **C 端静态包**：
   - 新建 `app/i18n/locales/ja.json`（页面固定文案）；
   - `nuxt.config` i18n 模块 `locales` 数组追加 `{ code: 'ja', language: 'ja', file: 'ja.json' }`（RTL 语言加 `dir: 'rtl'`）。

> 若只做“站点动态文案”多语言（页面固定文案暂不翻译），步骤 2 可跳过，C 端固定文案会 fallback 到英文。

## 5. 语言启用/停用

- 后台 i18n 面板 `locales` 多选控制启用集合；AppHeader 下拉只显示已启用语言。
- 未启用语言的历史 URL（如 `/de/`）由 Nuxt i18n 正常处理，站点配置中无该语言时回退 defaultLocale。

## 6. 已有语言包

| code | 语言 | RTL | 静态包 | 站点 translations |
|---|---|---|---|---|
| en | English | - | en.json | ✓ |
| zh | 简体中文 | - | zh.json | ✓ |
| ar | العربية | ✓ | ar.json | ✓ |
| de | Deutsch | - | de.json | ✓ |
| fr | Français | - | fr.json | ✓ |

扩展候选（localeOptions 已内置标签）：es / ja / ko / pt / ru / it / nl / pl / tr。
