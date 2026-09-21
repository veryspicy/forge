<template>
  <span class="inline-flex items-center gap-2">
    <span
      class="inline-block px-3 py-1 rounded-full text-xs font-medium"
      :class="statusClass"
    >
      {{ statusLabel }}
    </span>
    <!-- 资金状态与履约状态分离展示：退款类资金状态额外标注，不覆盖履约状态 -->
    <span
      v-if="paymentLabel"
      class="inline-block px-3 py-1 rounded-full text-xs font-medium"
      :class="paymentClass"
    >
      {{ paymentLabel }}
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ status: string; paymentStatus?: string | null }>(),
  {
    paymentStatus: null,
  }
)
const { t } = useI18n()

const statusClass = computed(() => {
  const map: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-blue-100 text-blue-800',
    paid: 'bg-blue-100 text-blue-800',
    processing: 'bg-indigo-100 text-indigo-800',
    shipped: 'bg-purple-100 text-purple-800',
    delivered: 'bg-green-100 text-green-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-red-100 text-red-800',
    refunded: 'bg-red-100 text-red-800',
    partially_refunded: 'bg-orange-100 text-orange-800',
  }
  return map[props.status] || 'bg-gray-100 text-gray-800'
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: t('orders.pending'),
    confirmed: t('orders.confirmed'),
    paid: t('orders.paid'),
    processing: t('orders.processing'),
    shipped: t('orders.shipped'),
    delivered: t('orders.delivered'),
    completed: t('orders.completed'),
    cancelled: t('orders.cancelled'),
    refunded: t('orders.refunded'),
    partially_refunded: t('orders.partiallyRefunded'),
  }
  return map[props.status] || props.status
})

/** 资金状态徽标：仅在 refunded / partially_refunded 时显示；履约状态已是退款态时不重复 */
const paymentLabel = computed(() => {
  if (['refunded', 'partially_refunded'].includes(String(props.status))) return ''
  const paymentStatus = String(props.paymentStatus || '')
  if (paymentStatus === 'refunded') return t('orders.refunded')
  if (paymentStatus === 'partially_refunded') return t('orders.partiallyRefunded')
  return ''
})

const paymentClass = computed(() => {
  const map: Record<string, string> = {
    refunded: 'bg-red-100 text-red-800',
    partially_refunded: 'bg-orange-100 text-orange-800',
  }
  return map[String(props.paymentStatus)] || 'bg-gray-100 text-gray-800'
})
</script>
