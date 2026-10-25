<!--
  Forge — Admin 详情块画布渲染（方案 A：编辑态即 C 端最终效果）
  与 portal-web/app/components/products/DetailBlocks.vue 渲染结构同构、视觉对齐。
  同步约定：C 端 DetailBlocks.vue 样式/结构变更时，须同步维护本组件。
  契约对齐 backend ProductService.DETAIL_BLOCK_FIELDS：
  rich_text(title/html/align) / image(title/images/caption) / image_text(title/image/html/layout)
  / spec_table(title/columns/rows) / features(title/items) / faq(title/items) / video(title/url/poster)
  admin 使用 UnoCSS（presetWind3），C 端 Tailwind 专属类（prose/primary-500/group-open 等）由 scoped CSS 兜底。
-->
<script setup lang="ts">
type Block = Record<string, any>;

defineProps<{ block: Block }>();

function alignClass(align?: string): string {
  if (align === 'center') return 'text-center';
  if (align === 'right') return 'text-right';
  return '';
}

function asText(v: unknown): string {
  if (typeof v === 'string') return v;
  if (v && typeof v === 'object') {
    const obj = v as Record<string, unknown>;
    return String(obj.label ?? obj.name ?? obj.value ?? obj.question ?? obj.answer ?? '');
  }
  return String(v ?? '');
}

// 卖点项：字符串直接返回；对象优先拼接 label + value（与 C 端 featureText 一致）
function featureText(v: unknown): string {
  if (typeof v === 'string') return v;
  if (v && typeof v === 'object') {
    const obj = v as Record<string, unknown>;
    const label = String(obj.label ?? obj.name ?? '');
    const value = String(obj.value ?? '');
    if (label && value) return `${label}: ${value}`;
    return label || value;
  }
  return String(v ?? '');
}

function normalizedItems(items: unknown[]): string[] {
  return (items || []).map(featureText).filter(Boolean);
}

// faq.items：`问题|答案` 字符串或 { question/answer, label/value } 对象（与 C 端 faqItems 一致）
function faqItems(items: unknown[]): { q: string; a: string }[] {
  return (items || [])
    .map((raw) => {
      if (raw && typeof raw === 'object') {
        const obj = raw as Record<string, unknown>;
        return { q: asText(obj.question ?? obj.label ?? obj.q), a: asText(obj.answer ?? obj.value ?? obj.a) };
      }
      const text = String(raw ?? '');
      const sep = text.indexOf('|');
      return sep >= 0 ? { q: text.slice(0, sep).trim(), a: text.slice(sep + 1).trim() } : { q: text, a: '' };
    })
    .filter((i) => i.q);
}

// spec_table.rows：`名称=值` 字符串数组或 { label/value } 对象数组（与 C 端一致）
function normalizedRows(rows?: unknown[]): Record<string, string>[] {
  return (rows || []).map((raw) => {
    if (raw && typeof raw === 'object') {
      const obj = raw as Record<string, unknown>;
      const out: Record<string, string> = {};
      for (const [k, v] of Object.entries(obj)) out[k] = asText(v);
      return out;
    }
    const text = String(raw ?? '');
    const eq = text.indexOf('=');
    return eq >= 0 ? { [text.slice(0, eq).trim()]: text.slice(eq + 1).trim() } : { value: text };
  });
}

function rowCells(row: Record<string, string>): string[] {
  const keys = Object.keys(row);
  if (keys.length === 0) return ['', ''];
  return keys.map((k) => row[k]);
}
</script>

<template>
  <div>
    <!-- 富文本 -->
    <section v-if="block.type === 'rich_text'" class="canvas-prose" :class="alignClass(block.align)">
      <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
      <div v-if="block.html" class="canvas-rich-text" v-html="block.html" />
    </section>

    <!-- 图片 -->
    <section v-else-if="block.type === 'image'">
      <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
      <div
        v-if="block.images && block.images.length"
        class="grid gap-4"
        :class="block.images.length > 1 ? 'sm:grid-cols-2' : ''"
      >
        <figure
          v-for="(img, i) in block.images"
          :key="i"
          class="rounded-xl overflow-hidden bg-gray-100"
        >
          <img :src="img" :alt="block.caption || block.title || ''" class="w-full h-auto object-cover" loading="lazy" />
        </figure>
      </div>
      <p v-if="block.caption" class="mt-2 text-sm text-gray-500 text-center">{{ block.caption }}</p>
    </section>

    <!-- 图文 -->
    <section
      v-else-if="block.type === 'image_text'"
      class="grid md:grid-cols-2 gap-6 items-center"
      :style="block.layout === 'right' ? { direction: 'rtl' } : {}"
    >
      <div class="md:[direction:ltr]">
        <img
          v-if="block.image"
          :src="block.image"
          :alt="block.title || ''"
          class="w-full h-auto rounded-xl object-cover bg-gray-100"
          loading="lazy"
        />
      </div>
      <div class="md:[direction:ltr]">
        <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
        <div v-if="block.html" class="canvas-rich-text" v-html="block.html" />
      </div>
    </section>

    <!-- 规格表 -->
    <section v-else-if="block.type === 'spec_table'">
      <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
      <div class="overflow-x-auto rounded-lg border border-gray-200">
        <table class="w-full text-sm">
          <thead v-if="block.columns && block.columns.length" class="bg-gray-50">
            <tr>
              <th
                v-for="(col, i) in block.columns"
                :key="i"
                class="px-4 py-2 text-left font-medium text-gray-700"
              >
                {{ col }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in normalizedRows(block.rows)" :key="i" class="border-t border-gray-100">
              <td
                v-for="(cell, j) in rowCells(row)"
                :key="j"
                class="px-4 py-2 text-gray-900 align-top"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 卖点列表 -->
    <section v-else-if="block.type === 'features'">
      <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
      <ul v-if="block.items && block.items.length" class="space-y-2.5">
        <li
          v-for="(item, i) in normalizedItems(block.items)"
          :key="i"
          class="flex items-start gap-2.5 text-gray-700 leading-relaxed"
        >
          <span class="canvas-feature-dot" />
          <span>{{ item }}</span>
        </li>
      </ul>
    </section>

    <!-- FAQ 折叠 -->
    <section v-else-if="block.type === 'faq'">
      <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
      <div v-if="block.items && block.items.length" class="space-y-2">
        <details
          v-for="(item, i) in faqItems(block.items)"
          :key="i"
          class="canvas-faq-item"
        >
          <summary class="canvas-faq-summary">
            <span>{{ item.q }}</span>
            <span class="canvas-faq-plus">+</span>
          </summary>
          <p class="canvas-faq-answer">{{ item.a }}</p>
        </details>
      </div>
    </section>

    <!-- 视频 -->
    <section v-else-if="block.type === 'video'">
      <h2 v-if="block.title" class="canvas-block-title">{{ block.title }}</h2>
      <video
        v-if="block.url"
        controls
        preload="metadata"
        :poster="block.poster || ''"
        class="w-full rounded-xl bg-black aspect-video"
      >
        <source :src="block.url" />
        浏览器不支持视频标签
      </video>
    </section>
  </div>
</template>

<style scoped>
/* 块标题：与 C 端 text-xl font-bold text-gray-900 mb-3 对齐 */
.canvas-block-title {
  font-size: 1.25rem;
  line-height: 1.75rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 0.75rem;
}

/* 富文本正文：与 C 端 prose + text-gray-700 leading-relaxed 对齐 */
.canvas-rich-text {
  color: #374151;
  line-height: 1.625;
  word-break: break-word;
}
.canvas-rich-text :deep(p) {
  margin-top: 0;
  margin-bottom: 0.75rem;
}
.canvas-rich-text :deep(p:last-child) {
  margin-bottom: 0;
}
.canvas-rich-text :deep(strong) {
  font-weight: 700;
  color: #111827;
}
.canvas-rich-text :deep(em) {
  font-style: italic;
}
.canvas-rich-text :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}
.canvas-rich-text :deep(ul) {
  list-style: disc;
  padding-left: 1.25rem;
  margin: 0.5rem 0;
}
.canvas-rich-text :deep(ol) {
  list-style: decimal;
  padding-left: 1.25rem;
  margin: 0.5rem 0;
}
.canvas-rich-text :deep(h1),
.canvas-rich-text :deep(h2),
.canvas-rich-text :deep(h3),
.canvas-rich-text :deep(h4) {
  font-weight: 700;
  color: #111827;
  margin: 1rem 0 0.5rem;
}
.canvas-rich-text :deep(h1) {
  font-size: 1.5rem;
}
.canvas-rich-text :deep(h2) {
  font-size: 1.25rem;
}
.canvas-rich-text :deep(h3) {
  font-size: 1.125rem;
}
.canvas-rich-text :deep(h4) {
  font-size: 1rem;
}
.canvas-rich-text :deep(blockquote) {
  border-left: 4px solid #e5e7eb;
  padding-left: 1rem;
  margin: 0.75rem 0;
  color: #6b7280;
}
.canvas-rich-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.75rem 0;
  font-size: 0.875rem;
}
.canvas-rich-text :deep(th),
.canvas-rich-text :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.375rem 0.5rem;
  text-align: left;
}
.canvas-rich-text :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}
/* 富文本渲染内容媒体约束：与 C 端 rich-content 对齐 */
.canvas-rich-text :deep(img),
.canvas-rich-text :deep(video) {
  width: 100% !important;
  max-width: min(100%, 1080px);
  height: auto !important;
  display: block;
  margin: 0.75rem auto;
  border-radius: 0.5rem;
}

/* 卖点圆点：与 C 端 bg-primary-500（oklch(0.58 0.14 145) 绿色）对齐 */
.canvas-feature-dot {
  margin-top: 0.375rem;
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 9999px;
  flex-shrink: 0;
  background: oklch(0.58 0.14 145);
}

/* FAQ 折叠：与 C 端 details/summary 对齐（group-open:rotate-45 由 details[open] 兜底） */
.canvas-faq-item {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background: #fff;
}
.canvas-faq-summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #111827;
}
.canvas-faq-summary::-webkit-details-marker {
  display: none;
}
.canvas-faq-plus {
  color: #9ca3af;
  transition: transform 0.2s ease;
  font-size: 1.125rem;
  line-height: 1;
}
.canvas-faq-item[open] .canvas-faq-plus {
  transform: rotate(45deg);
}
.canvas-faq-answer {
  padding: 0 1rem 0.75rem;
  font-size: 0.875rem;
  color: #4b5563;
  line-height: 1.625;
}
</style>
