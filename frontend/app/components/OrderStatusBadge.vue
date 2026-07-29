<template>
  <span
    class="inline-block px-3 py-1 rounded-full text-xs font-medium"
    :class="statusClass"
  >
    {{ statusLabel }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()
const { t } = useI18n()

const statusClass = computed(() => {
  const map: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-blue-100 text-blue-800',
    shipped: 'bg-purple-100 text-purple-800',
    delivered: 'bg-green-100 text-green-800',
    cancelled: 'bg-red-100 text-red-800',
  }
  return map[props.status] || 'bg-gray-100 text-gray-800'
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: t('orders.pending'),
    confirmed: t('orders.confirmed'),
    shipped: t('orders.shipped'),
    delivered: t('orders.delivered'),
    cancelled: t('orders.cancelled'),
  }
  return map[props.status] || props.status
})
</script>
