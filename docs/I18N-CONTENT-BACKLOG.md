# 站点内容多语言补录待办（ar / de / fr）

> 状态：**待业务侧录入**（技术链路已就绪，缺内容）。最后核对：2026-11-06。

## 1. 现状事实（2026-11-06 核对）

站点语言唯一数据源：`site_profiles.config.i18n.locales = ["en","zh","ar","de","fr"]`，`defaultLocale = "en"`（DEV-RULES §12）。

CMS `content` 表实测行数：

| locale | 行数 | 说明 |
|--------|------|------|
| en | 11 | 全部 `published`，正文齐全 |
| zh | 11 | 全部 `published`，正文齐全 |
| ar | 0 | 缺失 → 走回退 |
| de | 0 | 缺失 → 走回退 |
| fr | 0 | 缺失 → 走回退 |

**回退链路已验证生效**（不是 404）：

```
GET /api/v1/content/faqs?locale=ar  →  200，data.locale = "en"（返回 en 行，id 与 en 一致）
GET /ar/faqs                          →  200，页面渲染 en 正文
GET /ar/__not-exist                   →  404，错误页 lang="ar" dir="rtl"
```

前端渲染时以响应体 `data.locale` 判定是否发生回退（`ContentPage.vue`），后端保证 `请求语言 → 站点默认 → en` 三级回退（`content_service`）。

## 2. 待补录清单（11 页 × 3 语言 = 33 条）

录入入口：Admin → 内容管理 → 选择页面 → 语言下拉选 `ar / de / fr` → 从英文原文翻译后保存并发布。

| # | slug | 英文标题 | ar | de | fr |
|---|------|----------|----|----|----|
| 1 | faqs | Frequently Asked Questions | ☐ | ☐ | ☐ |
| 2 | shipping | Shipping Information | ☐ | ☐ | ☐ |
| 3 | returns | Returns & Exchanges | ☐ | ☐ | ☐ |
| 4 | contact | Contact Us | ☐ | ☐ | ☐ |
| 5 | story | Our Story | ☐ | ☐ | ☐ |
| 6 | sustainability | Sustainability | ☐ | ☐ | ☐ |
| 7 | blog | The Forge Blog | ☐ | ☐ | ☐ |
| 8 | careers | Careers at Forge | ☐ | ☐ | ☐ |
| 9 | privacy | Privacy Policy | ☐ | ☐ | ☐ |
| 10 | terms | Terms of Service | ☐ | ☐ | ☐ |
| 11 | cookies | Cookie Policy | ☐ | ☐ | ☐ |

录入注意：

- `slug` 必须与英文严格一致（唯一约束 `uq_content_slug_locale`），只改 `locale`。
- `ar` 正文为 RTL：正文 HTML 不要硬编码 `dir="ltr"` / `text-align:left`，方向由 `<html dir="rtl">` 交给浏览器镜像。
- 法务类页面（privacy / terms / cookies）涉及真实法律主体信息，**禁止机翻后直接发布**，需法务确认。

## 3. SEO 待决策项

多语言页当前未产出 `hreflang` 备用链接。内容补齐前不建议声明 `ar/de/fr` 的 hreflang（会指向英文内容，属重复内容风险）；内容补齐后再按 §4 验证并加 `useLocaleHead` 的备用链接。

## 4. 补齐后的验证命令

```powershell
# 1) 行数应为 en/zh/ar/de/fr 各 11
podman exec forge-postgres psql -U postgres -d forge -c "SELECT locale, count(*) FROM content GROUP BY locale ORDER BY locale;"

# 2) API 不再回退（data.locale 应等于请求 locale）
foreach ($l in @('ar','de','fr')) { (& curl.exe -s "http://127.0.0.1:8080/api/v1/content/faqs?locale=$l") -join "" }

# 3) 页面渲染与方向
& curl.exe -s -H "Accept: text/html" "http://127.0.0.1:8080/ar/faqs" | Select-Object -First 1
```

## 5. 前置条件与纪律

- 内容改动走 Admin 表单或 migration，**不要在本地直连数据库写库**（DEV-RULES §4）；确需批量 SQL 时在容器内执行并先备份。
- 补录属于数据变更，提交前先在 C 端 `/ar`、`/de`、`/fr` 三处实测渲染，再同步 SEO 决策。
