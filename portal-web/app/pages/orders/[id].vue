<template>
  <div class="min-h-screen bg-gray-50 py-8">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Loading -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"/>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>

      <template v-else-if="order">
        <!-- Breadcrumb -->
        <nav class="flex mb-6 text-sm text-gray-500">
          <button class="hover:text-gray-700" @click="navigateTo('/orders')">{{ $t('orders.orders') }}</button>
          <svg class="w-4 h-4 mx-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
          <span class="text-gray-900 font-medium">#{{ order.order_number || order.id }}</span>
        </nav>

        <!-- Order Header -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <div class="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 class="text-2xl font-bold text-gray-900">
                {{ $t('orders.order') }} #{{ order.order_number || order.id }}
              </h1>
              <p class="text-sm text-gray-500 mt-1">
                {{ $t('orders.placedOn') }} {{ formatDate(order.created_at || order.date) }}
              </p>
            </div>
            <div class="flex items-center space-x-3">
              <OrderStatusBadge :status="order.status" size="lg" />
              <button
                v-if="canCancel"
                class="px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                @click="showCancelModal = true"
              >
                {{ $t('orders.cancelOrder') }}
              </button>
              <button
                v-if="canConfirmReceipt"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
                @click="doConfirmReceipt"
              >
                {{ $t('orders.confirmReceipt') }}
              </button>
              <button
                v-if="canReturn"
                class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                @click="openReturnModal"
              >
                {{ $t('returns.requestReturn') }}
              </button>
              <button
                v-if="canDeleteOrder"
                class="px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                @click="askDeleteOrder"
              >
                {{ $t('orders.deleteOrder') }}
              </button>
              <button
                v-if="canPay"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                @click="openPayModal"
              >
                {{ $t('orders.pay') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Order Progress -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.tracking') }}</h2>
          <ol class="flex w-full items-start">
            <li
              v-for="(step, idx) in orderSteps"
              :key="step.key"
              class="relative flex-1 flex flex-col items-center min-w-0"
            >
              <div class="flex items-center w-full">
                <div
                  :class="[
                    'h-1 flex-1 rounded-full transition-colors',
                    idx === 0 ? 'bg-transparent' : (orderSteps[idx - 1].completed ? 'bg-indigo-600' : 'bg-gray-200')
                  ]"
                />
                <div
                  :class="[
                    'relative z-10 flex items-center justify-center w-10 h-10 rounded-full border-2 flex-shrink-0',
                    step.completed
                      ? 'bg-indigo-600 border-indigo-600'
                      : step.active
                      ? 'border-indigo-600 bg-white'
                      : 'border-gray-300 bg-white'
                  ]"
                >
                  <svg
                    v-if="step.completed"
                    class="w-5 h-5 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  <div
                    v-else-if="step.active"
                    class="w-3 h-3 rounded-full bg-indigo-600"
                  />
                  <span v-else class="text-gray-400 text-sm">{{ idx + 1 }}</span>
                </div>
                <div
                  :class="[
                    'h-1 flex-1 rounded-full transition-colors',
                    idx === orderSteps.length - 1 ? 'bg-transparent' : (step.completed ? 'bg-indigo-600' : 'bg-gray-200')
                  ]"
                />
              </div>
              <p
                :class="[
                  'mt-2 px-1 text-center text-sm font-medium leading-tight',
                  step.completed || step.active ? 'text-gray-900' : 'text-gray-400'
                ]"
              >
                {{ $t(`orders.step.${step.key}`) }}
              </p>
              <p v-if="step.date" class="mt-0.5 text-xs text-gray-500">{{ step.date }}</p>
            </li>
          </ol>
        </div>

        <!-- Shipment Tracking -->
        <div v-if="shipments.length > 0" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.shipmentTracking') }}</h2>
          <div v-for="s in shipments" :key="s.id" class="mb-6 last:mb-0 border border-gray-200 rounded-lg p-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
              <div>
                <span class="text-gray-500">{{ $t('orders.carrier') }}:</span>
                <span class="ml-2 font-medium">{{ s.carrier }}</span>
              </div>
              <div>
                <span class="text-gray-500">{{ $t('orders.trackingNumber') }}:</span>
                <a v-if="s.tracking_url" :href="s.tracking_url" target="_blank" class="ml-2 font-medium text-indigo-600 hover:underline">
                  {{ s.tracking_number }}
                </a>
                <span v-else class="ml-2 font-medium text-indigo-600">{{ s.tracking_number }}</span>
              </div>
              <div>
                <span class="text-gray-500">{{ $t('orders.trackingStatus') }}:</span>
                <span class="ml-2 font-medium">{{ s.status }}</span>
              </div>
              <div v-if="s.estimated_delivery">
                <span class="text-gray-500">{{ $t('orders.estimatedDelivery') }}:</span>
                <span class="ml-2 font-medium">{{ formatDate(s.estimated_delivery) }}</span>
              </div>
            </div>
            <!-- Events Timeline -->
            <div v-if="(s.events || []).length > 0" class="relative pl-6 border-l-2 border-gray-200 space-y-4">
              <div v-for="(evt, ei) in s.events" :key="ei" class="relative">
                <div class="absolute -left-[25px] w-3 h-3 rounded-full border-2 border-indigo-500 bg-white"/>
                <p class="text-sm font-medium text-gray-900">{{ evt.status || evt.description || evt.label || $t('orders.trackingUpdate') }}</p>
                <p class="text-xs text-gray-500">{{ evt.location || '' }}</p>
                <p class="text-xs text-gray-400">{{ formatDateTime(evt.timestamp || evt.date || evt.time) }}</p>
              </div>
            </div>
            <p v-else class="text-sm text-gray-500 italic">{{ $t('orders.noTrackingEvents') }}</p>
          </div>
        </div>
        <div v-else-if="!loading && ['shipped', 'delivered'].includes((order.status || '').toLowerCase())" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ $t('orders.shipmentTracking') }}</h2>
          <p class="text-sm text-gray-500">{{ $t('orders.noShipment') }}</p>
        </div>

        <!-- Order Items -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.items') }}</h2>
          <ul class="divide-y divide-gray-200">
            <li
              v-for="(item, idx) in (order.items || order.products || [])"
              :key="idx"
              class="py-4 flex items-center"
            >
              <div class="h-16 w-16 rounded-md bg-gray-100 overflow-hidden flex-shrink-0">
                <img
                  v-if="item.image || item.product_image"
                  :src="item.image || item.product_image"
                  :alt="item.name || item.product_name"
                  class="h-full w-full object-cover"
                >
                <div v-else class="h-full w-full flex items-center justify-center text-gray-400">
                  <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div class="ml-4 flex-1">
                <p class="text-sm font-medium text-gray-900">{{ item.name || item.product_name }}</p>
                <p class="text-sm text-gray-500 mt-0.5">{{ $t('orders.qty') }}: {{ item.quantity }}</p>
              </div>
              <div class="text-right">
                <p class="text-sm font-medium text-gray-900">{{ formatPrice(item.price || item.unit_price) }}</p>
                <p class="text-sm text-gray-500 mt-0.5">{{ formatPrice((item.price || item.unit_price) * item.quantity) }}</p>
                <div v-if="canReview" class="mt-2">
                  <span v-if="isReviewed(item.id)" class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-500">
                    <svg class="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                    {{ $t('reviews.reviewed') }}
                  </span>
                  <button
                    v-else
                    class="px-3 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                    @click="openReviewModal(item)"
                  >
                    {{ $t('reviews.write') }}
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <!-- Order Summary -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.orderSummary') }}</h2>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">{{ $t('orders.subtotal') }}</dt>
              <dd class="text-gray-900">{{ formatPrice(order.subtotal || order.sub_total) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">{{ $t('orders.tax') }}</dt>
              <dd class="text-gray-900">{{ formatPrice(order.tax || 0) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">{{ $t('orders.shipping') }}</dt>
              <dd class="text-gray-900">{{ formatPrice(order.shipping_cost || order.shipping || 0) }}</dd>
            </div>
            <div v-if="order.discount || order.coupon_discount" class="flex justify-between text-green-600">
              <dt>{{ $t('orders.discount') }}</dt>
              <dd>-{{ formatPrice(order.discount || order.coupon_discount || 0) }}</dd>
            </div>
            <div class="flex justify-between border-t border-gray-200 pt-2 mt-2">
              <dt class="text-base font-semibold text-gray-900">{{ $t('orders.total') }}</dt>
              <dd class="text-base font-semibold text-gray-900">{{ formatPrice(order.total || order.total_amount) }}</dd>
            </div>
          </dl>
        </div>

        <!-- Shipping Address -->
        <div v-if="order.shipping_address" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('orders.shippingAddress') }}</h2>
          <address class="text-sm text-gray-600 not-italic">
            <p class="font-medium text-gray-900">{{ order.shipping_address.name || order.shipping_address.recipient_name }}</p>
            <p>{{ order.shipping_address.line1 || order.shipping_address.address_line1 }}</p>
            <p v-if="order.shipping_address.line2 || order.shipping_address.address_line2">
              {{ order.shipping_address.line2 || order.shipping_address.address_line2 }}
            </p>
            <p>
              {{ order.shipping_address.city }}
              <template v-if="order.shipping_address.state">, {{ order.shipping_address.state }}</template>
              {{ order.shipping_address.postal_code || order.shipping_address.zip }}
            </p>
            <p>{{ order.shipping_address.country }}</p>
          </address>
        </div>

        <!-- Returns & Refunds -->
        <div v-if="myReturns.length > 0" class="bg-white rounded-lg shadow p-6 mt-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ $t('returns.myReturns') }}</h2>
          <ul class="divide-y divide-gray-200">
            <li
              v-for="r in myReturns"
              :key="r.return_number"
              class="py-4 flex flex-wrap items-start justify-between gap-3"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center flex-wrap gap-2">
                  <span class="text-sm font-medium text-gray-900">#{{ r.return_number }}</span>
                  <span :class="['inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', returnStatusClass(r.status)]">
                    {{ returnStatusText(r.status) }}
                  </span>
                </div>
                <p class="text-sm text-gray-500 mt-1">{{ $t('returns.reasonLabel') }}: {{ returnReasonLabel(r.reason, t) }}</p>
                <p class="text-xs text-gray-400 mt-1">
                  {{ $t('returns.requestedAt') }} {{ formatDateTime(r.requested_at || r.created_at) }}
                  · {{ (r.items || []).length }} {{ $t('returns.itemsCount') }}
                </p>
                <p v-if="r.review_note" class="text-xs text-gray-500 mt-1">{{ r.review_note }}</p>

                <!-- 寄回物流：客户回填后在此追踪 -->
                <div v-if="r.tracking_number" class="mt-2 rounded-md bg-gray-50 border border-gray-200 px-3 py-2">
                  <p class="text-xs text-gray-500">{{ $t('returns.shipBackTracking') }}</p>
                  <p class="text-xs text-gray-900 mt-0.5">
                    {{ r.carrier }} · <span class="font-mono">{{ r.tracking_number }}</span>
                  </p>
                  <p v-if="r.shipped_at" class="text-xs text-gray-500 mt-0.5">
                    {{ $t('returns.shippedAt') }} {{ formatDateTime(r.shipped_at) }}
                  </p>
                  <p class="text-xs text-gray-400 mt-0.5">{{ formatPrice(r.refund_amount || 0) }} · {{ $t('returns.refundAfterReceive') }}</p>
                </div>
                <p v-else-if="canSubmitShipment(r)" class="text-xs text-amber-600 mt-2">
                  {{ $t('returns.trackingRequired') }}
                </p>
              </div>
              <div class="text-right">
                <p class="text-sm font-medium text-gray-900">{{ formatPrice(r.refund_amount || 0) }}</p>
                <button
                  v-if="canSubmitShipment(r)"
                  class="mt-2 px-3 py-1 rounded-md text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                  @click="openShipmentModal(r)"
                >
                  {{ r.tracking_number ? $t('returns.updateTracking') : $t('returns.submitTracking') }}
                </button>
                <button
                  v-if="canCancelReturn(r)"
                  class="mt-2 px-3 py-1 rounded-md text-xs font-medium border border-red-300 text-red-700 hover:bg-red-50"
                  @click="returnCancelTarget = r"
                >
                  {{ $t('returns.cancelRequest') }}
                </button>
              </div>
            </li>
          </ul>
        </div>
      </template>
    </div>

    <!-- Return Shipment Modal（寄回快递单号） -->
    <div v-if="showShipmentModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4 py-8">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="showShipmentModal = false"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-1">{{ $t('returns.shipmentModalTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-4">{{ $t('returns.shipmentModalHint') }}</p>

          <div v-if="shipmentError" class="mb-4 bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-800">
            {{ shipmentError }}
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('returns.carrier') }}</label>
            <input
              v-model="shipmentForm.carrier"
              type="text"
              maxlength="100"
              :placeholder="$t('returns.carrierPlaceholder')"
              class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
            >
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('returns.trackingNumber') }}</label>
            <input
              v-model="shipmentForm.tracking_number"
              type="text"
              maxlength="64"
              :placeholder="$t('returns.trackingNumberPlaceholder')"
              class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm font-mono"
            >
            <p class="text-xs text-gray-500 mt-1">{{ $t('returns.trackingHint') }}</p>
          </div>

          <div class="flex justify-end gap-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              @click="showShipmentModal = false"
            >
              {{ $t('common.cancel') }}
            </button>
            <button
              :disabled="shipmentSubmitting"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              @click="doSubmitShipment"
            >
              {{ shipmentSubmitting ? $t('returns.submitting') : $t('returns.submit') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Return Request Modal -->
    <div v-if="showReturnModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4 py-8">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="showReturnModal = false"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-2xl w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-1">{{ $t('returns.modalTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-4">{{ $t('returns.modalHint') }}</p>

          <div v-if="returnError" class="mb-4 bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-800">
            {{ returnError }}
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('returns.selectItems') }}</label>
            <p v-if="returnableItems.length === 0" class="text-sm text-gray-500">{{ $t('returns.noReturnableItems') }}</p>
            <ul v-else class="divide-y divide-gray-200 border border-gray-200 rounded-md">
              <li v-for="i in returnableItems" :key="i.order_item_id" class="p-3 flex items-start gap-3">
                <input
                  type="checkbox"
                  class="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600"
                  :checked="returnForm.selected[String(i.order_item_id)]"
                  @change="toggleReturnItem(i, ($event.target as HTMLInputElement).checked)"
                >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900">{{ i.name }}</p>
                  <p class="text-xs text-gray-500 mt-0.5">
                    {{ $t('returns.returnableQty') }}: {{ i.returnable_quantity }} · {{ formatPrice(i.unit_price) }}
                  </p>
                </div>
                <input
                  v-if="returnForm.selected[String(i.order_item_id)]"
                  type="number"
                  min="1"
                  :max="i.returnable_quantity"
                  class="w-20 border border-gray-300 rounded-md px-2 py-1 text-sm"
                  :value="returnForm.quantities[String(i.order_item_id)]"
                  @input="setReturnQty(i, Number(($event.target as HTMLInputElement).value))"
                >
              </li>
            </ul>
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('returns.reason') }}</label>
            <select
              v-model="returnForm.reason"
              class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">{{ $t('returns.reasonPlaceholder') }}</option>
              <option v-for="r in RETURN_REASONS" :key="r" :value="r">
                {{ $t(`returns.reason${r.charAt(0).toUpperCase()}${r.slice(1)}`) }}
              </option>
            </select>
          </div>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('returns.note') }}</label>
            <textarea
              v-model="returnForm.note"
              rows="3"
              :placeholder="$t('returns.notePlaceholder')"
              class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div class="flex items-center justify-between border-t border-gray-200 pt-4">
            <p class="text-sm text-gray-500">
              {{ $t('returns.refundEstimate') }}:
              <span class="font-medium text-gray-900">{{ formatPrice(returnRefundEstimate) }}</span>
            </p>
            <div class="flex space-x-3">
              <button
                class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                @click="showReturnModal = false"
              >
                {{ $t('common.cancel') }}
              </button>
              <button
                :disabled="returnSubmitting"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                @click="doSubmitReturn"
              >
                {{ returnSubmitting ? $t('returns.submitting') : $t('returns.submit') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Cancel Return Modal -->
    <div v-if="returnCancelTarget" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="returnCancelTarget = null"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('returns.cancelModalTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-6">
            {{ $t('returns.cancelConfirmText') }}
          </p>
          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="returnCancelTarget = null"
            >
              {{ $t('returns.keepRequest') }}
            </button>
            <button
              :disabled="returnCancelling"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              @click="doCancelReturn"
            >
              {{ returnCancelling ? $t('returns.cancelling') : $t('returns.cancelRequest') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Cancel Order Modal -->
    <div v-if="showCancelModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="showCancelModal = false"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('orders.cancelOrderTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-6">
            {{ $t('orders.cancelConfirmText') }}
          </p>
          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="showCancelModal = false"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              :disabled="cancelling"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
              @click="doCancelOrder"
            >
              {{ cancelling ? $t('orders.cancelling') : $t('orders.cancelOrder') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pay Order Modal -->
    <div v-if="showPayModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="showPayModal = false"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-1">{{ $t('orders.payTitle') }}</h3>
          <p class="text-sm text-gray-500 mb-4">{{ $t('orders.payMockNote') }}</p>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('checkout.paymentMethod') }}</label>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                class="border rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition"
                :class="payForm.method === 'card' ? 'border-indigo-600 ring-1 ring-indigo-600 text-indigo-700' : 'border-gray-300 text-gray-600 hover:border-gray-400'"
                @click="payForm.method = 'card'"
              >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V6a2 2 0 00-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/></svg>
                {{ $t('checkout.creditCard') }}
              </button>
              <button
                type="button"
                class="border rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition"
                :class="payForm.method === 'paypal' ? 'border-indigo-600 ring-1 ring-indigo-600 text-indigo-700' : 'border-gray-300 text-gray-600 hover:border-gray-400'"
                @click="payForm.method = 'paypal'"
              >
                <span class="font-bold italic">Pay<span class="text-blue-600">Pal</span></span>
                {{ $t('checkout.paypal') }}
              </button>
            </div>
          </div>

          <div v-if="payForm.method === 'card'" class="space-y-3 mb-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.cardName') }}</label>
              <input
                v-model.trim="payForm.card.name"
                type="text"
                :placeholder="$t('checkout.fullName')"
                class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.cardNumber') }}</label>
              <input
                v-model="cardNumberText"
                type="text"
                inputmode="numeric"
                maxlength="23"
                placeholder="4242 4242 4242 4242"
                class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.expiryDate') }}</label>
                <input
                  v-model.trim="payForm.card.expiry"
                  type="text"
                  inputmode="numeric"
                  maxlength="5"
                  placeholder="MM/YY"
                  class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('checkout.cardCvv') }}</label>
                <input
                  v-model.trim="payForm.card.cvv"
                  type="password"
                  inputmode="numeric"
                  maxlength="4"
                  placeholder="123"
                  class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
              </div>
            </div>
            <p v-if="cardError" class="text-xs text-red-600">{{ cardError }}</p>
          </div>

          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="showPayModal = false"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              :disabled="paying"
              class="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70"
              @click="doPay"
            >
              <span v-if="paying" class="inline-block w-4 h-4 mr-2 border-2 border-white/40 border-t-white rounded-full animate-spin"/>
              {{ paying ? $t('orders.paying') : $t('orders.pay') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Review Modal -->
    <div v-if="reviewTarget" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="reviewTarget = null"/>
        <div class="relative bg-white/85 backdrop-blur-2xl rounded-lg max-w-md w-full p-6 shadow-2xl ring-1 ring-white/60">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reviews.write') }} - {{ reviewTarget.name || reviewTarget.product_name }}
          </h3>

          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('reviews.rating') }}</label>
            <div class="flex gap-1">
              <button
                v-for="star in 5"
                :key="star"
                type="button"
                class="text-2xl focus:outline-none transition"
                :class="star <= reviewForm.rating ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-200'"
                @click="reviewForm.rating = star"
              >
                ★
              </button>
            </div>
            <p v-if="reviewError" class="text-xs text-red-600 mt-1">{{ reviewError }}</p>
          </div>

          <div class="space-y-3 mb-4">
            <input
              v-model.trim="reviewForm.title"
              type="text"
              maxlength="200"
              :placeholder="$t('reviews.titlePlaceholder')"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            >
            <textarea
              v-model.trim="reviewForm.content"
              rows="4"
              maxlength="5000"
              :placeholder="$t('reviews.contentPlaceholder')"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 resize-none"
            />
          </div>

          <div class="flex justify-end space-x-3">
            <button
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="reviewTarget = null"
            >
              {{ $t('orders.keepOrder') }}
            </button>
            <button
              :disabled="reviewSubmitting"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              @click="doSubmitReview"
            >
              {{ reviewSubmitting ? $t('reviews.submitting') : $t('reviews.submit') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Order Confirm Modal -->
    <div v-if="showDeleteModal" class="fixed inset-0 z-50 overflow-y-auto" aria-modal="true">
      <div class="flex min-h-full items-center justify-center p-4 text-center">
        <div class="fixed inset-0 bg-gray-500/40 backdrop-blur-md transition-opacity" @click="closeDeleteModal" />
        <div
          class="relative bg-white/85 backdrop-blur-2xl rounded-2xl shadow-2xl ring-1 ring-white/60 max-w-md w-full text-left"
        >
          <div class="px-6 pt-5 pb-4 border-b">
            <h3 class="text-lg font-semibold text-gray-900">{{ $t('orders.deleteOrder') }}</h3>
            <p class="text-sm text-gray-500 mt-1">{{ $t('orders.deleteConfirmText') }}</p>
          </div>
          <div class="px-6 py-4 border-t flex justify-end gap-3">
            <button
              class="px-4 py-2 text-sm border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition font-medium"
              @click="closeDeleteModal"
            >
              {{ $t('common.cancel') }}
            </button>
            <button
              class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="deleting"
              @click="doDeleteOrder"
            >
              {{ $t('orders.confirmDelete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import OrderStatusBadge from '~/components/OrderStatusBadge.vue'
import { useOrderStore } from '~/stores/order'
import { useApi } from '~/composables/useApi'
import { useCurrency } from '~/composables/useCurrency'
import { RETURN_REASON_CODES, returnReasonLabel } from '~/utils/returnReason'

definePageMeta({
  middleware: 'auth',
})

const route = useRoute()
const orderStore = useOrderStore()
const { fetchShipments, fetchReturnEligibility, createReturn, fetchMyReturns, cancelReturn, submitReturnShipment } = useApi()
const { toMessage, resolveCode } = useApiError()
const { toast } = useToast()
const { t } = useI18n()
const order = ref<any>(null)
const shipments = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const showCancelModal = ref(false)
const cancelling = ref(false)

// --- 售后服务（退货/退款 RMA） ---
const returnEligibility = ref<any>(null)
const myReturns = ref<any[]>([])
const showReturnModal = ref(false)
const returnSubmitting = ref(false)
const returnError = ref('')
const returnCancelTarget = ref<any>(null)
const returnCancelling = ref(false)
// 退货寄回物流（审核通过后由客户回填快递单号）
const shipmentTarget = ref<any>(null)
const showShipmentModal = ref(false)
const shipmentSubmitting = ref(false)
const shipmentError = ref('')
const shipmentForm = ref<{ carrier: string; tracking_number: string }>({ carrier: '', tracking_number: '' })
const returnForm = ref<{
  reason: string
  note: string
  refund_method: string
  selected: Record<string, boolean>
  quantities: Record<string, number>
}>({ reason: '', note: '', refund_method: 'original', selected: {}, quantities: {} })

// ---- Payment ----
const showPayModal = ref(false)
const paying = ref(false)
const cardError = ref('')
const payForm = ref({
  method: 'card' as 'card' | 'paypal',
  card: { name: '', number: '', expiry: '', cvv: '' },
})

// ---- Review ----
const reviewTarget = ref<any>(null)
const reviewSubmitting = ref(false)
const reviewError = ref('')
const reviewForm = ref({ rating: 0, title: '', content: '' })

const orderId = computed(() => route.params.id as string)

const canCancel = computed(() => {
  if (!order.value) return false
  const status = (order.value.status || '').toLowerCase()
  return status === 'pending' || status === 'processing'
})

const canPay = computed(() => {
  if (!order.value || order.value.deleted_at) return false
  const status = (order.value.status || '').toLowerCase()
  // 终态订单（已取消/已退款/已完成）一律不可支付，避免「已取消仍可支付」
  if (['cancelled', 'refunded', 'completed'].includes(status)) return false
  if (['refunded', 'partially_refunded'].includes(String(order.value.payment_status || ''))) return false
  return order.value.payment_status === 'unpaid' || status === 'pending'
})

const canConfirmReceipt = computed(() => {
  if (!order.value) return false
  return (order.value.status || '').toLowerCase() === 'shipped'
})

const canDeleteOrder = computed(() => {
  if (!order.value || order.value.deleted_at) return false
  const status = (order.value.status || '').toLowerCase()
  return ['delivered', 'cancelled', 'refunded'].includes(status)
})

const canReview = computed(() => {
  if (!order.value) return false
  const status = (order.value.status || '').toLowerCase()
  return status === 'delivered' && !order.value.deleted_at
})

const isReviewed = (itemId: string) => orderStore.reviewedItemIds.has(String(itemId))

const openPayModal = () => {
  payForm.value = { method: order.value?.payment_method === 'paypal' ? 'paypal' : 'card', card: { name: '', number: '', expiry: '', cvv: '' } }
  cardError.value = ''
  showPayModal.value = true
}

// 卡号按 4 位分组展示（仅保留数字），避免空格/连字符被判为无效卡号
function formatCardNumber(value?: string | null): string {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 19)
  return digits.replace(/(\d{4})(?=\d)/g, '$1 ')
}

// Luhn 校验：拦截明显错误的卡号，减少无效支付尝试
function isValidCardNumber(value?: string | null): boolean {
  const digits = String(value || '').replace(/\D/g, '')
  if (digits.length < 13 || digits.length > 19) return false
  let sum = 0
  let double = false
  for (let i = digits.length - 1; i >= 0; i -= 1) {
    let digit = Number(digits[i])
    if (double) {
      digit *= 2
      if (digit > 9) digit -= 9
    }
    sum += digit
    double = !double
  }
  return sum % 10 === 0
}

const cardNumberText = computed({
  get: () => formatCardNumber(payForm.value.card.number),
  set: (value: string) => {
    payForm.value.card.number = String(value || '').replace(/\D/g, '').slice(0, 19)
  },
})

const doPay = async () => {
  cardError.value = ''
  if (payForm.value.method === 'card') {
    const card = payForm.value.card
    if (!card.name || !card.number || !card.expiry || !card.cvv) {
      cardError.value = t('checkout.invalidCard')
      return
    }
    if (!isValidCardNumber(card.number)) {
      cardError.value = t('checkout.invalidCardNumber')
      return
    }
  }
  paying.value = true
  try {
    // 模拟真实支付网关跳转/风控耗时，避免“秒付成功”造成不真实感
    await new Promise((resolve) => setTimeout(resolve, 1500))
    await orderStore.payOrder(orderId.value, {
      payment_method: payForm.value.method,
      card: payForm.value.method === 'card' ? { ...payForm.value.card } : undefined,
    })
    showPayModal.value = false
    toast.success(t('orders.paySuccess'))
    await reloadOrder()
  } catch (err: any) {
    cardError.value = toMessage(err)
  } finally {
    paying.value = false
  }
}

const doConfirmReceipt = async () => {
  if (!confirm(t('orders.confirmReceiptHint') as string)) return
  try {
    await orderStore.confirmReceipt(orderId.value)
    toast.success(t('orders.completed'))
    await reloadOrder()
  } catch (err: any) {
    error.value = toMessage(err)
  }
}

// 删除确认：应用内弹窗（替代原生 confirm）
const showDeleteModal = ref(false)
const deleting = ref(false)

const askDeleteOrder = () => {
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
}

const doDeleteOrder = async () => {
  deleting.value = true
  try {
    await orderStore.deleteOrder(orderId.value)
    toast.success(t('orders.orderDeleted'))
    showDeleteModal.value = false
    navigateTo('/orders')
  } catch (err: any) {
    error.value = toMessage(err)
  } finally {
    deleting.value = false
  }
}

const openReviewModal = (item: any) => {
  reviewTarget.value = item
  reviewForm.value = { rating: 0, title: '', content: '' }
  reviewError.value = ''
}

const doSubmitReview = async () => {
  reviewError.value = ''
  if (!reviewTarget.value || reviewForm.value.rating < 1) {
    reviewError.value = t('reviews.rateRequired')
    return
  }
  reviewSubmitting.value = true
  try {
    await orderStore.submitReview({
      order_number: orderId.value,
      order_item_id: String(reviewTarget.value.id),
      rating: reviewForm.value.rating,
      title: reviewForm.value.title || undefined,
      content: reviewForm.value.content || undefined,
    })
    reviewTarget.value = null
    toast.success(t('reviews.success'))
    await orderStore.loadMyReviews()
  } catch (err: any) {
    reviewError.value = toMessage(err)
  } finally {
    reviewSubmitting.value = false
  }
}

const reloadOrder = async () => {
  await orderStore.loadOrderDetail(orderId.value)
  order.value = orderStore.currentOrder
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const { formatPrice } = useCurrency()

const orderSteps = computed(() => {
  if (!order.value) return []
  const status = (order.value.status || '').toLowerCase()
  const steps = [
    { key: 'ordered', completed: false, active: false, date: '' },
    { key: 'confirmed', completed: false, active: false, date: '' },
    { key: 'shipped', completed: false, active: false, date: '' },
    { key: 'delivered', completed: false, active: false, date: '' },
  ]

  // 订单状态机：pending(未支付) -> confirmed(已支付待发货) -> shipped(已发货) -> delivered(已确认收货)
  // 对应步骤点亮：下单->已下单；支付->待发货；卖家发货->已发货；确认收货->已确认收货
  const statusOrder = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
  const currentIdx = statusOrder.indexOf(status)

  if (status === 'delivered') {
    steps.forEach((s) => { s.completed = true })
  } else if (currentIdx >= 0) {
    const stepIdx = currentIdx === 0 ? 0 : (currentIdx === 1 || currentIdx === 2 ? 1 : 2)
    for (let i = 0; i < steps.length; i++) {
      if (i < stepIdx) steps[i].completed = true
      else if (i === stepIdx) steps[i].active = true
    }
  } else if (status === 'cancelled') {
    // 已取消：已下单步骤保持完成，其余置灰由模板默认展示
    steps[0].completed = true
  }

  return steps
})

const doCancelOrder = async () => {
  cancelling.value = true
  try {
    await orderStore.cancelOrder(orderId.value, 'User requested cancellation')
    showCancelModal.value = false
    toast.success(t('orders.cancelled'))
    await reloadOrder()
  } catch (err: any) {
    error.value = toMessage(err)
  } finally {
    cancelling.value = false
  }
}

// --- Returns: helpers ---
const RETURN_REASONS = RETURN_REASON_CODES
const OPEN_RETURN_STATUSES = ['requested', 'approved', 'received']

const returnableItems = computed(() => {
  const items = returnEligibility.value?.items || []
  return items.filter((i: any) => Number(i.returnable_quantity || 0) > 0)
})

const selectedReturnItems = computed(() =>
  returnableItems.value.filter((i: any) => returnForm.value.selected[String(i.order_item_id)])
)

const hasOpenReturn = computed(() =>
  myReturns.value.some((r: any) => OPEN_RETURN_STATUSES.includes(String(r.status || '').toLowerCase()))
)

const canReturn = computed(() =>
  !!returnEligibility.value?.eligible && returnableItems.value.length > 0 && !hasOpenReturn.value
)

const returnRefundEstimate = computed(() =>
  selectedReturnItems.value.reduce((sum: number, i: any) => {
    const qty = Number(returnForm.value.quantities[String(i.order_item_id)] || 0)
    return sum + Number(i.unit_price || 0) * qty
  }, 0)
)

const canCancelReturn = (r: any) => OPEN_RETURN_STATUSES.includes(String(r?.status || '').toLowerCase())

const returnStatusText = (status?: string) => t(`returns.status.${String(status || '').toLowerCase()}`)

const returnStatusClass = (status?: string) => {
  switch (String(status || '').toLowerCase()) {
    case 'requested': return 'bg-amber-50 text-amber-700'
    case 'approved': return 'bg-blue-50 text-blue-700'
    case 'received': return 'bg-indigo-50 text-indigo-700'
    case 'refunded': return 'bg-green-50 text-green-700'
    case 'rejected': return 'bg-red-50 text-red-700'
    default: return 'bg-gray-100 text-gray-600'
  }
}

const clampReturnQty = (item: any, value: number) => {
  const max = Number(item.returnable_quantity || 0)
  const qty = Number.isFinite(value) ? Math.floor(value) : max
  return Math.min(Math.max(qty, 1), Math.max(max, 1))
}

const toggleReturnItem = (item: any, checked: boolean) => {
  const key = String(item.order_item_id)
  returnForm.value.selected[key] = checked
}

const setReturnQty = (item: any, value: number) => {
  const key = String(item.order_item_id)
  returnForm.value.quantities[key] = clampReturnQty(item, value)
}

const openReturnModal = () => {
  const selected: Record<string, boolean> = {}
  const quantities: Record<string, number> = {}
  returnableItems.value.forEach((i: any) => {
    const key = String(i.order_item_id)
    selected[key] = true
    quantities[key] = Number(i.returnable_quantity || 1)
  })
  returnForm.value = { reason: '', note: '', refund_method: 'original', selected, quantities }
  returnError.value = ''
  showReturnModal.value = true
}

const loadReturns = async () => {
  try {
    const res: any = await fetchMyReturns({ order_number: orderId.value, page_size: 50 })
    myReturns.value = res?.items || []
  } catch {
    myReturns.value = []
  }
}

const loadReturnEligibility = async () => {
  try {
    returnEligibility.value = await fetchReturnEligibility(orderId.value)
  } catch {
    returnEligibility.value = null
  }
}

const doSubmitReturn = async () => {
  const items = selectedReturnItems.value
    .map((i: any) => ({
      order_item_id: String(i.order_item_id),
      quantity: clampReturnQty(i, Number(returnForm.value.quantities[String(i.order_item_id)] || 0)),
    }))
  if (items.length === 0) {
    returnError.value = t('returns.errors.itemsRequired')
    return
  }
  if (!returnForm.value.reason) {
    returnError.value = t('returns.errors.reasonRequired')
    return
  }
  returnSubmitting.value = true
  returnError.value = ''
  try {
    await createReturn({
      order_number: orderId.value,
      items,
      reason: returnForm.value.reason,
      note: returnForm.value.note || undefined,
      refund_method: returnForm.value.refund_method,
    })
    showReturnModal.value = false
    toast.success(t('returns.applySuccess'))
    await Promise.all([loadReturns(), loadReturnEligibility()])
  } catch (err: any) {
    returnError.value = toMessage(err)
  } finally {
    returnSubmitting.value = false
  }
}

const doCancelReturn = async () => {
  if (!returnCancelTarget.value) return
  returnCancelling.value = true
  try {
    await cancelReturn(String(returnCancelTarget.value.return_number), 'Cancelled by customer')
    returnCancelTarget.value = null
    toast.success(t('returns.cancelled'))
    await Promise.all([loadReturns(), loadReturnEligibility()])
  } catch (err: any) {
    toast.error(toMessage(err))
  } finally {
    returnCancelling.value = false
  }
}

// --- Returns: 寄回物流（审核通过后客户回填快递单号） ---
const canSubmitShipment = (r: any) => String(r?.status || '').toLowerCase() === 'approved'

const openShipmentModal = (r: any) => {
  shipmentTarget.value = r
  shipmentForm.value = {
    carrier: r?.carrier || '',
    tracking_number: r?.tracking_number || '',
  }
  shipmentError.value = ''
  showShipmentModal.value = true
}

const doSubmitShipment = async () => {
  if (!shipmentTarget.value) return
  const carrier = shipmentForm.value.carrier.trim()
  const trackingNumber = shipmentForm.value.tracking_number.trim()
  if (!carrier || !trackingNumber) {
    shipmentError.value = t('returns.errors.shipmentRequired')
    return
  }
  shipmentSubmitting.value = true
  shipmentError.value = ''
  try {
    await submitReturnShipment(String(shipmentTarget.value.return_number), {
      carrier,
      tracking_number: trackingNumber,
    })
    showShipmentModal.value = false
    shipmentTarget.value = null
    toast.success(t('returns.shipmentSubmitted'))
    await Promise.all([loadReturns(), loadReturnEligibility()])
  } catch (err: any) {
    shipmentError.value = toMessage(err)
  } finally {
    shipmentSubmitting.value = false
  }
}

onMounted(async () => {
  try {
    await orderStore.loadOrderDetail(orderId.value)
    order.value = orderStore.currentOrder
    orderStore.loadMyReviews()
    // Fetch shipments
    try {
      shipments.value = await fetchShipments(orderId.value)
    } catch {
      shipments.value = []
    }
    // 售后：可退性 + 已有退货单
    await Promise.all([loadReturnEligibility(), loadReturns()])
    // 列表页“去支付”跳转时自动唤起支付弹窗
    if (route.query.pay === '1' && canPay.value) {
      openPayModal()
    }
  } catch (err: any) {
    const code = resolveCode(err)
    const httpStatus: number | undefined = err?.status ?? err?.response?.status
    if (code === 'NOT_FOUND' || code === 'ORDER_NOT_FOUND' || httpStatus === 404) {
      showError({ statusCode: 404, statusMessage: 'NOT_FOUND' })
      return
    }
    error.value = toMessage(err)
  } finally {
    loading.value = false
  }
})
</script>