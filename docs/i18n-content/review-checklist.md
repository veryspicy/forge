---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_78970564d9e311f1bc42525400638852
    ReservedCode1: QCXCRWo2Xj0Sp1GBTXEaK7YP9NvEF1+Nsj5DpFMnGUeQZpLvjz+pOx8ynLhA+3PZ2a+jbA+fVSWssM6omkE1g0zb+k+FtyX8biUSC48Rgo6w7GsYPZcncSEWzyUWWlacSx0A3EEEh3ghoi/r1RBfMBVsnX/JN8f7BarWsCpDPp/TIoi6Fr/HbGX5N0I=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_78970564d9e311f1bc42525400638852
    ReservedCode2: QCXCRWo2Xj0Sp1GBTXEaK7YP9NvEF1+Nsj5DpFMnGUeQZpLvjz+pOx8ynLhA+3PZ2a+jbA+fVSWssM6omkE1g0zb+k+FtyX8biUSC48Rgo6w7GsYPZcncSEWzyUWWlacSx0A3EEEh3ghoi/r1RBfMBVsnX/JN8f7BarWsCpDPp/TIoi6Fr/HbGX5N0I=
---

# Forge 多语言 CMS 内容补齐 — 对标评审与上线前确认清单

- 语言：`ar` / `de` / `fr`，共 11 页 × 3 = 33 篇
- 草案：`docs/i18n-content/draft-{de,fr,ar}.json`
- 同行证据：`docs/i18n-content/benchmark-pet-dtc.md`（Wild One / Fable / maxbone / Tuft+Paw / BARK 官网实查，2026-11-06）
- 导入器：`temp/import_i18n_content.py`（默认 dry-run，`--apply` 才写库，写库前自动 pg_dump content 表）
- 状态：**草案，未经你确认不写库、不提交**

---

## 1. 事实来源纪律

三语正文中的所有政策数值，全部取自 `content` 表现有 `locale=en` 正文，未引入任何新承诺：

| 事实项 | 取值 | 来源 |
|---|---|---|
| 免运费门槛 | 50 USD | en / shipping |
| 订单处理时效 | 2 个工作日 | en / shipping、faqs |
| 退货窗口 | 30 天 | en / returns、faqs |
| 退款到账 | 收货验收后 5–10 个工作日 | en / returns |
| 破损/错发申报 | 7 天内、需照片 | en / returns |
| 客服邮箱与响应 | tandong917@outlook.com，1 个工作日 | en / contact、faqs |
| 支付方式 | 信用卡/借记卡、PayPal、Apple Pay、Google Pay | en / faqs |
| 配送范围 | 全球 | en / faqs、shipping |
| 可持续承诺 | 可回收包装、负责任采购、合并运输、部分收益支持动物福利（均不量化） | en / sustainability |

无法从现有站点确证的业务变量一律留 `{{...}}` 占位符，未编造。

---

## 2. 行业对标（benchmark-pet-dtc.md 实测数据）

| 维度 | Forge 现状 | 行业基准（5 站） | 差距判定 | 处理 |
|---|---|---|---|---|
| 免运门槛 | 50 USD 全场 | Wild One $90；Tuft+Paw US $50 / CA $100；maxbone 无门槛按重量；Fable、BARK 未披露 | 处于行业主流区间内，**无需改** | 三语版如实呈现 |
| 退货窗口 | 30 天 | Wild One 30、Fable 30、Tuft+Paw 30、maxbone 14、BARK 不受理 | 优于或持平主流 | 保持 30 天 |
| 退货运费 | en 未明确 | 4 家有数据的全部由客户承担 | **en 侧缺失口径** | 三语版明确写为客户承担，需你确认 |
| 欧盟撤回权 | en 未提 | Wild One 明确列 14 天 EU 撤回权例外 | 面向德法**法定必备** | de/fr 版已单列 14 天撤回权小节 |
| 区域配送时效 | en 有标题无内容（空） | 北美 5–10、国际 7–10 等 | **en 侧内容缺陷** | 三语版给出 4 档区间，标注为待确认建议值 |
| 国际关税归属 | 客户承担 | Wild One / maxbone 同为客户承担 | 一致 | 保持 |
| sustainability 独立页 | 有 | 5 站全部 404，无独立页 | Forge 差异化亮点 | 保留，但不得加未核实的认证或比例 |
| 法务主体信息 | 已收编为站点配置项 | 各站均有完整主体/注册信息 | **待补齐**（补齐即解锁发布） | 见 4.1 节 |

结论：Forge 的商业政策本身与行业主流一致，不需要为国际化改写政策；真正的缺口是**法务主体信息**与**区域时效**这两类事实，不是文案质量。

---

## 3. 本地化强制合规差异（已体现在草案）

| 市场 | 强制/惯例要求 | 草案落点 |
|---|---|---|
| de | 14 天法定撤回权（BGB §355/§356），与商业 30 天并行 | returns 增「Gesetzliches Widerrufsrecht (EU)」小节 |
| de | 退货运费由客户承担须事先告知 | returns 明确写明，并在 review_flags 标记需正式 Widerrufsbelehrung |
| de | Impressum（§5 DDG）：名称、可送达地址、邮箱+第二快联系渠道、VAT ID | contact/terms 留 `{{COMPANY_LEGAL_NAME}}`、`{{COMPANY_ADDRESS}}` 占位并标记 |
| de | 价格标示（PAngV）：面向消费者须说明是否含增值税 | terms 标记待确认，未擅自写「含 MwSt.」 |
| de | Cookie 同意｜§25 TDDDG | cookies 增「Einwilligung」小节 |
| fr | 14 天 rétractation（Code de la consommation） | returns 增「Droit de rétractation légal (UE)」小节 |
| fr | mentions légales（LCEN）：éditeur、RCS、hébergeur | contact/terms 占位 `{{RCS_NUMBER}}` 并标记 |
| fr | CNIL 同意撤回、消费调解（médiation） | cookies 增「Consentement」；terms 标记需补调解人信息 |
| ar | GCC 电商合规：阿语完整披露退换条件、运费、配送时效、投诉渠道 | shipping/returns/contact 全覆盖；未硬编码 `dir="ltr"`，正文交由上游 RTL 处理 |
| ar | 市场未定 → 货币与支付渠道不可预设 | 沿用 USD，review_flags 标记 SAR/AED 与 Mada/STC Pay 待定 |

---

## 4. 决策项（阻塞发布，逐项给结论即可）

### 4.1 已落地：第 1–5 项收编为 Admin 站点配置项

前 5 项（法务主体变量）已从硬编码占位符改为站点配置驱动，无需改代码即可填写：

- **填写入口**：Admin → 站点设置 → **法务信息**（配置键 `site_profiles.config.legal`）
- **字段**：`companyLegalName` / `registeredAddress` / `privacyEmail` / `jurisdiction` / `lastUpdated` / `vatId` / `rcsNumber`
- **渲染方式**：三语草案正文保留 `{{...}}` 占位符入库，C 端 `/api/v1/content/{slug}` 按站点 `i18n.defaultLocale` 与请求语言注入并本地化日期（en `November 6, 2026` / de `6. November 2026` / fr `6 novembre 2026` / ar `6 نوفمبر 2026` / zh `2026年11月6日`）
- **发布闸门**：占位符无法解析（对应字段为空或未知占位符）时，该语言内容按未就绪跳过，返回 404，不会把半成品法务页推上线
- **导入器**：`temp/import_i18n_content.py` 默认读取站点当前法务配置判定可发布性，并打印「待补字段」清单

| 字段 | 对应占位符 | 使用页面 | 当前值 |
|---|---|---|---|
| companyLegalName | `{{COMPANY_LEGAL_NAME}}` | privacy / terms（de/fr/ar） | 待填 |
| registeredAddress | `{{COMPANY_ADDRESS}}` | privacy / terms（de/fr/ar） | 待填 |
| privacyEmail | `{{PRIVACY_EMAIL}}` | privacy（de/fr/ar） | 待填（建议 privacy@ 自有域名） |
| jurisdiction | `{{JURISDICTION}}` | terms（de/fr/ar） | 待填 |
| lastUpdated | `{{LAST_UPDATED}}` | privacy / terms | 待填（填日期按语言自动本地化） |
| vatId | `{{VAT_ID}}` | de Impressum 扩展 | 待填（有则填） |
| rcsNumber | `{{RCS_NUMBER}}` | fr mentions légales 扩展 | 待填（有则填） |

补齐后即可对法务页执行发布（三语 privacy/terms），无需再改代码。

### 4.2 仍待决策

| # | 事项 | 影响 | 现状 |
|---|---|---|---|
| 6 | 货币策略：de/fr 是否改 EUR 含税展示、ar 是否改 SAR/AED | 涉及德国 PAngV 与法国 TTC 强制 | 现沿用 USD |
| 7 | 区域时效 4 档是否认可（北美 5–10 / 欧洲 5–9 / 中东 7–12 / 其他 7–14） | 三语 shipping | 建议值，需按真实承运商替换 |
| 8 | 退货运费是否维持「客户承担」 | 三语 returns | 按同行主流拟定 |
| 9 | 是否新增 Impressum / mentions légales 独立页（现有 11 页清单外） | 德国、法国市场合规完整度 | 未建 |
| 10 | ar 目标市场：沙特 / 阿联酋 / 泛阿拉伯 | 隐私法适用、支付渠道、货币 | 未定 |
| 11 | 三个法务页是否走外部法务定稿 | privacy/terms/cookies 共 9 篇 | 草案已备，标记 do_not_publish |

第 4.1 节字段未填时，导入器会自动把对应页面存为 `draft` 而非 `published`，C 端也不会返回，不会把占位符推上线。

---

## 5. 顺手发现的 en 侧缺陷（建议另开 fix）

1. `privacy` 与 `terms` 的 en 正文中各自混入**两版模板并重复**（同一段「Overview」出现两次、「Agreement to Terms」出现两次）。
2. `privacy`/`terms` 仍含 `[privacy@example.com]`、`[company legal address]`、`[currency]`、`[jurisdiction]`、`[Month DD, YYYY]` 等英文占位符，正在被真实用户看到。
3. `shipping` 的「Estimated transit times by region:」后面**没有任何表格内容**。

三语草案未复制以上缺陷。

---

## 6. 导入与验证

```powershell
cd D:\codeRepo\forge

# 1) 干跑：只生成 SQL，不动库
python temp\import_i18n_content.py

# 2) 确认后执行（写库前自动备份 content 表数据到 temp/）
python temp\import_i18n_content.py --apply

# 3) 校验行数：应 de/fr/ar 各 11 行
podman exec forge-postgres psql -U postgres -d forge -c "SELECT locale, status, count(*) FROM content GROUP BY locale, status ORDER BY locale;"

# 4) 校验 API 不再回退：data.locale 应为 ar/de/fr 本身
curl.exe -s "http://localhost:8080/api/v1/content/shipping?locale=de"
curl.exe -s "http://localhost:8080/api/v1/content/returns?locale=fr"
curl.exe -s "http://localhost:8080/api/v1/content/faqs?locale=ar"

# 5) 校验 RTL 与页面 200
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:3000/ar/faqs
```

内容为数据层变更，不涉及源码，无需重建镜像；若仅 Admin 缓存不刷新，按需清缓存即可。
*（内容由AI生成，仅供参考）*
