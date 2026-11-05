/**
 * CMS 内容骨架模板
 *
 * 用途：后台「内容管理 → 编辑」页一键插入结构化 HTML 骨架，避免每次从空白 textarea 手搓排版。
 * 约定：
 *  - 只用 C 端富文本基线（.prose-forge）已定义的元素：h2/h3/p/ul/ol/li/table/blockquote/hr/a/strong
 *  - 不写内联 style（后端 sanitize_html 只保留 text-align，其它一律丢弃，写了也无效）
 *  - 骨架内文案为起草提示，运营替换即可；占位统一用 [方括号]
 *  - 语言维度与 content.locale 对齐：en / zh 提供完整版，ar / de / fr 暂复用 en 骨架（避免多语言漂移）
 */

export interface ContentTemplate {
  /** 模板唯一标识 */
  key: string
  /** 后台下拉展示名 */
  label: string
  /** 适用 slug，仅用于下拉排序与提示 */
  slugs: string[]
  /** 按 locale 提供骨架；缺省回落到 en */
  bodies: Record<string, string>
}

const PRIVACY_EN = `<h2>Overview</h2>
<p>This Privacy Policy explains what information Forge collects, how we use it, and the choices you have. It applies to our website, mobile experience, and related services.</p>
<p><strong>Last updated:</strong> [Month DD, YYYY]</p>

<h2>Information We Collect</h2>
<ul>
  <li><strong>Information you give us</strong> — name, email, shipping address, phone number, order details, and any content you submit through support or reviews.</li>
  <li><strong>Payment information</strong> — processed by our payment providers; we do not store full card numbers.</li>
  <li><strong>Information collected automatically</strong> — device type, browser, IP address, pages viewed, and cookie identifiers.</li>
  <li><strong>Pet profile data</strong> — breed, age, weight, and preferences you choose to share so we can tailor recommendations.</li>
</ul>

<h2>How We Use Information</h2>
<ol>
  <li>Fulfil orders, process payments, and handle returns.</li>
  <li>Provide customer support and respond to enquiries.</li>
  <li>Personalise product recommendations and site content.</li>
  <li>Detect fraud, secure our services, and comply with legal obligations.</li>
  <li>Send marketing communications where permitted — you can opt out at any time.</li>
</ol>

<h2>Sharing</h2>
<p>We share information only with service providers that help us operate the store (payments, logistics, analytics, email), and where required by law. We never sell personal information.</p>

<h2>Cookies</h2>
<p>We use strictly necessary cookies to keep the store working and optional cookies to measure performance and personalise content. You can manage preferences in your browser or via our cookie banner.</p>

<h2>Your Rights</h2>
<p>Depending on where you live, you may request access, correction, deletion, or a portable copy of your data, and object to certain processing. Contact us at [privacy@example.com] to exercise these rights.</p>

<h2>Data Retention</h2>
<p>We retain order records for as long as required for tax and accounting purposes, and other data only as long as needed for the purposes described above.</p>

<h2>Contact</h2>
<p>Questions about this policy? Email [privacy@example.com] or write to [company legal address].</p>`

const PRIVACY_ZH = `<h2>概述</h2>
<p>本隐私政策说明 Forge 收集哪些信息、我们如何使用这些信息，以及您可以选择的权利。本政策适用于我们的网站、移动端体验及相关服务。</p>
<p><strong>最后更新：</strong>[YYYY 年 MM 月 DD 日]</p>

<h2>我们收集的信息</h2>
<ul>
  <li><strong>您主动提供的信息</strong> —— 姓名、邮箱、收货地址、联系电话、订单信息，以及您通过客服或评价提交的内容。</li>
  <li><strong>支付信息</strong> —— 由支付服务商处理，我们不存储完整银行卡号。</li>
  <li><strong>自动收集的信息</strong> —— 设备型号、浏览器、IP 地址、访问页面与 Cookie 标识。</li>
  <li><strong>宠物档案信息</strong> —— 您选择填写的品种、年龄、体重与偏好，用于个性化推荐。</li>
</ul>

<h2>信息使用方式</h2>
<ol>
  <li>完成订单履约、处理支付与退换货。</li>
  <li>提供客户服务并回复您的咨询。</li>
  <li>提供个性化商品推荐与内容展示。</li>
  <li>防范欺诈、保障服务安全并履行法定义务。</li>
  <li>在获得许可的前提下发送营销信息，您可随时退订。</li>
</ol>

<h2>信息共享</h2>
<p>我们仅在必要范围内与帮助我们运营店铺的服务商共享信息（支付、物流、数据分析、邮件服务），或在法律要求时披露。我们不会出售个人信息。</p>

<h2>Cookie</h2>
<p>我们使用必要 Cookie 保障站点正常运行，并使用可选 Cookie 统计性能与个性化内容。您可通过浏览器或 Cookie 提示管理偏好。</p>

<h2>您的权利</h2>
<p>根据您所在地区的法律，您有权请求访问、更正、删除或获取个人信息的可携带副本，并可反对特定处理行为。请通过 [privacy@example.com] 联系我们行使上述权利。</p>

<h2>数据保存期限</h2>
<p>订单记录按税务与会计要求保存；其他信息仅在实现上述目的所需期限内保存。</p>

<h2>联系我们</h2>
<p>如对本政策有疑问，请发送邮件至 [privacy@example.com]，或来信至 [公司法定地址]。</p>`

const TERMS_EN = `<h2>Agreement to Terms</h2>
<p>By accessing or ordering from Forge, you agree to these Terms of Service. If you do not agree, please do not use the site.</p>
<p><strong>Last updated:</strong> [Month DD, YYYY]</p>

<h2>Orders and Acceptance</h2>
<p>All orders are offers to purchase and are subject to acceptance and availability. We may cancel an order if the item is out of stock, priced in error, or if we suspect fraudulent activity — you will be refunded in full.</p>

<h2>Pricing and Payment</h2>
<ul>
  <li>Prices are shown in [currency] and exclude taxes and shipping unless stated otherwise.</li>
  <li>Duties and import taxes for international orders are the responsibility of the recipient.</li>
  <li>Payment is captured at checkout through our payment providers.</li>
</ul>

<h2>Shipping and Delivery</h2>
<p>Delivery estimates are provided in good faith but are not guaranteed. Risk of loss passes to you upon delivery to the address provided.</p>

<h2>Returns and Refunds</h2>
<p>Unused items in original packaging may be returned within [30] days of delivery. Certain items — opened food, personalised goods, and hygiene-sensitive products — are non-returnable unless faulty. Refunds are issued to the original payment method.</p>

<h2>Acceptable Use</h2>
<p>You agree not to misuse the site, including scraping, reverse engineering, submitting unlawful content, or interfering with security features.</p>

<h2>Intellectual Property</h2>
<p>All content, trademarks, and designs on this site are owned by [company name] or its licensors and may not be used without written permission.</p>

<h2>Limitation of Liability</h2>
<p>To the maximum extent permitted by law, our liability for any claim arising from your use of the site is limited to the amount you paid for the relevant order.</p>

<h2>Governing Law</h2>
<p>These terms are governed by the laws of [jurisdiction], without regard to conflict of law rules.</p>

<h2>Contact</h2>
<p>Questions about these terms? Email [support@example.com].</p>`

const TERMS_ZH = `<h2>条款接受</h2>
<p>访问或通过 Forge 下单，即表示您同意本服务条款。如不同意，请停止使用本站。</p>
<p><strong>最后更新：</strong>[YYYY 年 MM 月 DD 日]</p>

<h2>订单与接受</h2>
<p>所有订单均为购买要约，需经我们接受并视库存情况确认。若商品缺货、价格错误或存在欺诈嫌疑，我们可取消订单并全额退款。</p>

<h2>价格与支付</h2>
<ul>
  <li>商品价格以 [币种] 计价，除另有说明外不含税费与运费。</li>
  <li>跨境订单产生的关税与进口税由收件人承担。</li>
  <li>支付在结算环节通过支付服务商完成。</li>
</ul>

<h2>配送与交付</h2>
<p>预计送达时间为善意预估，不构成保证。商品送达您提供的地址后，毁损风险转移至您。</p>

<h2>退换与退款</h2>
<p>未使用且包装完好的商品可在签收后 [30] 天内申请退货。已开封食品、定制商品及卫生类商品除质量问题外不支持退货。退款将退回原支付渠道。</p>

<h2>使用规范</h2>
<p>您同意不以任何方式滥用本站，包括爬取数据、反向工程、提交违法内容或干扰安全机制。</p>

<h2>知识产权</h2>
<p>本站内容、商标与设计归 [公司名称] 或其许可方所有，未经书面许可不得使用。</p>

<h2>责任限制</h2>
<p>在法律允许的最大范围内，因您使用本站产生的任何索赔，我们的责任上限为您就该笔订单实际支付的金额。</p>

<h2>适用法律</h2>
<p>本条款受 [司法辖区] 法律管辖，不适用冲突法规则。</p>

<h2>联系我们</h2>
<p>如对本条款有疑问，请发送邮件至 [support@example.com]。</p>`

const SHIPPING_EN = `<h2>Processing Time</h2>
<p>Orders are packed within [1-2] business days. Orders placed on weekends or public holidays begin processing the next business day.</p>

<h2>Shipping Options</h2>
<table>
  <thead>
    <tr><th>Method</th><th>Estimated delivery</th><th>Cost</th></tr>
  </thead>
  <tbody>
    <tr><td>Standard</td><td>[5-8] business days</td><td>[free over $49]</td></tr>
    <tr><td>Express</td><td>[2-4] business days</td><td>[$12.00]</td></tr>
    <tr><td>International</td><td>[7-14] business days</td><td>Calculated at checkout</td></tr>
  </tbody>
</table>

<h2>Tracking</h2>
<p>You will receive a tracking link by email once your parcel leaves our warehouse. Tracking can take up to 24 hours to update.</p>

<h2>Customs and Duties</h2>
<p>International orders may be subject to import duties and taxes levied by the destination country. These charges are the responsibility of the recipient.</p>

<h2>Lost or Damaged Parcels</h2>
<p>If a parcel arrives damaged, contact us within [48] hours with photos of the packaging and contents. For parcels marked delivered but not received, please check with neighbours and your local carrier first, then contact us within [7] days.</p>

<h2>Returns</h2>
<p>See our Returns Policy for eligibility and instructions. Return shipping is free for faulty items; otherwise the cost is borne by the customer unless stated otherwise.</p>`

const SHIPPING_ZH = `<h2>处理时效</h2>
<p>订单将在 [1-2] 个工作日内完成打包。周末与法定节假日下单的订单，将于下一个工作日开始处理。</p>

<h2>配送方式</h2>
<table>
  <thead>
    <tr><th>方式</th><th>预计送达</th><th>费用</th></tr>
  </thead>
  <tbody>
    <tr><td>标准配送</td><td>[5-8] 个工作日</td><td>[满 ¥299 免运费]</td></tr>
    <tr><td>加急配送</td><td>[2-4] 个工作日</td><td>[¥25.00]</td></tr>
    <tr><td>跨境配送</td><td>[7-14] 个工作日</td><td>结算时计算</td></tr>
  </tbody>
</table>

<h2>物流跟踪</h2>
<p>包裹出库后，我们会通过邮件发送物流单号与查询链接。物流信息可能需要 24 小时才会更新。</p>

<h2>关税与税费</h2>
<p>跨境订单可能产生目的地国家或地区征收的进口关税与税费，该费用由收件人承担。</p>

<h2>丢件与破损</h2>
<p>如包裹到货时已破损，请在 [48] 小时内联系我们并提供外包装与商品照片。若物流显示已签收但您未收到，请先与邻居及当地承运商确认，并在 [7] 天内联系我们。</p>

<h2>退货说明</h2>
<p>退货条件与流程见《退换与退款政策》。质量问题退货运费由我们承担；非质量原因退货运费由客户承担，另有说明除外。</p>`

const FAQ_EN = `<h2>Orders</h2>
<h3>How do I change or cancel an order?</h3>
<p>Contact us within [2] hours of placing the order. Once a parcel has been packed, changes may not be possible, but you can return the item after delivery.</p>
<h3>Do you ship internationally?</h3>
<p>Yes — we ship to [list of countries/regions]. Shipping costs and duties are calculated at checkout.</p>

<h2>Products</h2>
<h3>How do I choose the right size?</h3>
<p>Each product page includes a sizing guide based on weight and breed. If you are between sizes, we recommend the larger one for growing pets.</p>
<h3>Are your products suitable for sensitive pets?</h3>
<p>Our formulas list all ingredients and allergens. For pets with medical conditions, please consult your veterinarian before use.</p>

<h2>Shipping</h2>
<h3>When will my order arrive?</h3>
<p>Standard delivery takes [5-8] business days after dispatch. You will receive a tracking link by email.</p>

<h2>Returns</h2>
<h3>What is your return window?</h3>
<p>[30] days from delivery for unused items in original packaging. Opened food and hygiene products are non-returnable unless faulty.</p>

<h2>Support</h2>
<h3>How do I reach a human?</h3>
<p>Email [support@example.com] or use live chat. We reply within [1] business day, [Monday-Friday, 9:00-18:00 timezone].</p>`

const FAQ_ZH = `<h2>订单</h2>
<h3>如何修改或取消订单？</h3>
<p>请在下单后 [2] 小时内联系我们。包裹一旦完成打包可能无法修改，但您可在收货后申请退货。</p>
<h3>是否支持跨境配送？</h3>
<p>支持，可配送至 [国家/地区列表]。运费与关税在结算页计算。</p>

<h2>商品</h2>
<h3>如何选择合适的尺码？</h3>
<p>每个商品页均提供基于体重与品种的尺码建议。若介于两档之间，成长期宠物建议选择偏大尺码。</p>
<h3>敏感体质宠物可以使用吗？</h3>
<p>我们公开全部成分与过敏原信息。如宠物有疾病史，使用前请咨询兽医。</p>

<h2>配送</h2>
<h3>什么时候能收到货？</h3>
<p>标准配送在发货后 [5-8] 个工作日送达，物流单号将通过邮件发送。</p>

<h2>退换货</h2>
<h3>退货时限是多久？</h3>
<p>签收后 [30] 天内、商品未使用且包装完好可申请退货。已开封食品与卫生类商品除质量问题外不支持退货。</p>

<h2>客服支持</h2>
<h3>如何联系人工客服？</h3>
<p>发送邮件至 [support@example.com] 或使用在线客服。我们会在 [1] 个工作日内回复，服务时间为 [周一至周五 9:00-18:00]。 </p>`

export const CONTENT_TEMPLATES: ContentTemplate[] = [
  {
    key: 'privacy',
    label: '隐私政策 / Privacy Policy',
    slugs: ['privacy', 'privacy-policy'],
    bodies: { en: PRIVACY_EN, zh: PRIVACY_ZH }
  },
  {
    key: 'terms',
    label: '服务条款 / Terms of Service',
    slugs: ['terms', 'terms-of-service', 'tos'],
    bodies: { en: TERMS_EN, zh: TERMS_ZH }
  },
  {
    key: 'shipping',
    label: '配送政策 / Shipping & Returns',
    slugs: ['shipping', 'shipping-returns', 'delivery'],
    bodies: { en: SHIPPING_EN, zh: SHIPPING_ZH }
  },
  {
    key: 'faq',
    label: '常见问题 / FAQ',
    slugs: ['faqs', 'faq', 'help'],
    bodies: { en: FAQ_EN, zh: FAQ_ZH }
  }
]

/** 按 locale 取骨架内容；ar / de / fr 等未翻译语种回落到 en */
export function getTemplateBody(template: ContentTemplate, locale: string): string {
  return template.bodies[locale] ?? template.bodies.en ?? ''
}
