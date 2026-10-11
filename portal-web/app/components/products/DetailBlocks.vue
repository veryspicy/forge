<!-- Forge — Product Detail Blocks Renderer
契约对齐 backend ProductService.DETAIL_BLOCK_FIELDS：
rich_text(title/html/align) / image(title/images/caption) / image_text(title/image/html/layout)
/ spec_table(title/columns/rows) / features(title/items) / faq(title/items) / video(title/url/poster)
-->
<template>
  <div class="space-y-10">
    <template v-for="(block, idx) in blocks" :key="idx">
      <!-- 富文本 -->
      <section v-if="block.type === 'rich_text'" class="prose max-w-none" :class="alignClass(block.align)">
        <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
        <div v-if="block.html" class="text-gray-700 leading-relaxed" v-html="block.html" />
      </section>

      <!-- 图片 -->
      <section v-else-if="block.type === 'image'">
        <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
        <div v-if="block.images && block.images.length" class="grid gap-4" :class="block.images.length > 1 ? 'sm:grid-cols-2' : ''">
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
      <section v-else-if="block.type === 'image_text'" class="grid md:grid-cols-2 gap-6 items-center" :class="block.layout === 'right' ? 'md:[direction:rtl]' : ''">
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
          <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
          <div v-if="block.html" class="text-gray-700 leading-relaxed" v-html="block.html" />
        </div>
      </section>

      <!-- 规格表 -->
      <section v-else-if="block.type === 'spec_table'">
        <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
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

      <!-- 卖点列表（要点文案，Chewy 答案式短句） -->
      <section v-else-if="block.type === 'features'">
        <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
        <ul v-if="block.items && block.items.length" class="space-y-2.5">
          <li
            v-for="(item, i) in normalizedItems(block.items)"
            :key="i"
            class="flex items-start gap-2.5 text-gray-700 leading-relaxed"
          >
            <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0" />
            <span>{{ item }}</span>
          </li>
        </ul>
      </section>

      <!-- FAQ 折叠 -->
      <section v-else-if="block.type === 'faq'">
        <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
        <div v-if="block.items && block.items.length" class="space-y-2">
          <details
            v-for="(item, i) in faqItems(block.items)"
            :key="i"
            class="group border border-gray-200 rounded-lg bg-white"
          >
            <summary class="cursor-pointer list-none flex items-center justify-between gap-2 px-4 py-3 text-sm font-medium text-gray-900">
              <span>{{ item.q }}</span>
              <span class="text-gray-400 transition-transform group-open:rotate-45 text-lg leading-none">+</span>
            </summary>
            <p class="px-4 pb-3 text-sm text-gray-600 leading-relaxed">{{ item.a }}</p>
          </details>
        </div>
      </section>

      <!-- 视频 -->
      <section v-else-if="block.type === 'video'">
        <h2 v-if="block.title" class="text-xl font-bold text-gray-900 mb-3">{{ block.title }}</h2>
        <video
          v-if="block.url"
          controls
          preload="metadata"
          :poster="block.poster || ''"
          class="w-full rounded-xl bg-black aspect-video"
        >
          <source :src="block.url" />
          {{ $t('products.videoNotSupported') }}
        </video>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { DetailBlock } from '~/stores/product'

const props = defineProps<{ blocks: DetailBlock[] }>()

function alignClass(align?: string) {
  if (align === 'center') return 'text-center'
  if (align === 'right') return 'text-right'
  return ''
}

function asText(v: unknown): string {
  if (typeof v === 'string') return v
  if (v && typeof v === 'object') {
    const obj = v as Record<string, unknown>
    return String(obj.label ?? obj.name ?? obj.value ?? obj.question ?? obj.answer ?? '')
  }
  return String(v ?? '')
}

// 卖点项：字符串直接返回；对象优先拼接 label + value（如 "Material: BPA-free nylon"），无 label 时只取 value
function featureText(v: unknown): string {
  if (typeof v === 'string') return v
  if (v && typeof v === 'object') {
    const obj = v as Record<string, unknown>
    const label = String(obj.label ?? obj.name ?? '')
    const value = String(obj.value ?? '')
    if (label && value) return `${label}: ${value}`
    return label || value
  }
  return String(v ?? '')
}

// features.items：字符串数组，或 { label/name/value } 对象数组
function normalizedItems(items: unknown[]): string[] {
  return (items || []).map(featureText).filter(Boolean)
}

// faq.items：`问题|答案` 字符串或 { question/answer, label/value } 对象
function faqItems(items: unknown[]): { q: string; a: string }[] {
  return (items || [])
    .map((raw) => {
      if (raw && typeof raw === 'object') {
        const obj = raw as Record<string, unknown>
        return { q: asText(obj.question ?? obj.label ?? obj.q), a: asText(obj.answer ?? obj.value ?? obj.a) }
      }
      const text = String(raw ?? '')
      const sep = text.indexOf('|')
      return sep >= 0 ? { q: text.slice(0, sep).trim(), a: text.slice(sep + 1).trim() } : { q: text, a: '' }
    })
    .filter((i) => i.q)
}

// spec_table.rows：`名称=值` 字符串数组或 { label/value } 对象数组；columns 存在时按列对齐
function normalizedRows(rows?: unknown[]): Record<string, string>[] {
  return (rows || []).map((raw) => {
    if (raw && typeof raw === 'object') {
      const obj = raw as Record<string, unknown>
      const out: Record<string, string> = {}
      for (const [k, v] of Object.entries(obj)) out[k] = asText(v)
      return out
    }
    const text = String(raw ?? '')
    const eq = text.indexOf('=')
    return eq >= 0 ? { [text.slice(0, eq).trim()]: text.slice(eq + 1).trim() } : { value: text }
  })
}

// 无 columns 时把 { 键: 值 } 展开为两列；有 columns 时按对象键顺序取列
function rowCells(row: Record<string, string>): string[] {
  const keys = Object.keys(row)
  if (keys.length === 0) return ['', '']
  return keys.map((k) => row[k])
}
</script>
