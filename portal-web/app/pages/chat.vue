<template>
  <div class="max-w-6xl mx-auto px-3 sm:px-4 py-4 lg:py-8 lg:pb-8 flex flex-col gap-4 flex-1 min-h-0 overflow-hidden lg:h-auto lg:flex-none lg:overflow-visible lg:grid lg:gap-6 lg:grid-cols-[260px_1fr]">
    <!-- Mobile / narrow-screen toolbar：打开历史抽屉 -->
    <div class="flex items-center justify-between gap-2 sm:gap-3 lg:hidden">
      <button
        class="flex-1 min-h-[44px] inline-flex items-center justify-center gap-2 px-3 rounded-lg border bg-white dark:bg-stone-900 dark:border-neutral-700 text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:border-accent-400 active:bg-neutral-50 dark:active:bg-stone-800 transition"
        :aria-label="$t('chat.history') || 'History'"
        :aria-expanded="drawerOpen"
        @click="openDrawer"
      >
        <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <span class="truncate">{{ $t('chat.history') || 'History' }}</span>
        <span
          v-if="chatStore.conversations.length"
          class="px-1.5 py-0.5 rounded-full bg-accent-100 text-accent-700 text-[11px] font-semibold shrink-0"
        >{{ chatStore.conversations.length }}</span>
      </button>
      <button
        class="shrink-0 min-h-[44px] inline-flex items-center gap-1.5 px-3 rounded-lg bg-accent-600 text-white text-sm font-medium hover:bg-accent-500 active:bg-accent-700 transition"
        @click="newChat"
      >
        <span class="text-base leading-none">+</span>
        <span>{{ $t('chat.newConversation') || 'New chat' }}</span>
      </button>
    </div>

    <!-- 抽屉遮罩（仅窄屏生效） -->
    <div
      v-if="drawerOpen"
      class="fixed inset-0 z-40 bg-neutral-900/40 lg:hidden"
      @click="closeDrawer"
    />

    <!-- Conversation History：窄屏为左侧抽屉，lg+ 为常驻侧栏 -->
    <aside
      class="fixed inset-y-0 left-0 z-50 w-[280px] max-w-[85vw] transition-transform duration-300 ease-out lg:sticky lg:top-6 lg:self-start lg:z-auto lg:w-auto lg:max-w-none lg:translate-x-0"
      :class="drawerOpen ? 'translate-x-0' : '-translate-x-full'"
      :role="drawerOpen ? 'dialog' : 'complementary'"
      :aria-modal="drawerOpen ? 'true' : undefined"
      :aria-label="$t('chat.history') || 'History'"
    >
      <div class="h-full lg:h-auto flex flex-col bg-white dark:bg-stone-900 border-r lg:border lg:rounded-xl lg:shadow-sm overflow-hidden pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] lg:pt-0 lg:pb-0">
        <!-- 抽屉标题栏（窄屏可见） -->
        <div class="flex items-center justify-between px-4 h-12 border-b shrink-0 lg:hidden">
          <p class="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
            {{ $t('chat.history') || 'History' }}
          </p>
          <button
            class="w-11 h-11 -mr-2 flex items-center justify-center text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 text-2xl leading-none rounded-lg active:bg-neutral-100 dark:active:bg-stone-800"
            :aria-label="$t('chat.close') || 'Close'"
            @click="closeDrawer"
          >
            ×
          </button>
        </div>
        <button
          class="w-[calc(100%-1.5rem)] mx-3 mt-3 mb-2 px-3 py-2 rounded-lg bg-accent-600 text-white text-sm font-medium hover:bg-accent-500 transition shrink-0"
          @click="newChat"
        >
          {{ $t('chat.newConversation') || 'New chat' }}
        </button>
        <p class="px-4 pb-1 text-xs font-semibold text-neutral-400 uppercase tracking-wide">
          {{ $t('chat.history') || 'History' }}
        </p>
        <p v-if="chatStore.conversations.length === 0" class="px-4 py-2 text-xs text-neutral-400">
          {{ $t('chat.noHistory') || 'No conversations yet' }}
        </p>
        <ul class="space-y-1 px-3 pb-4 overflow-y-auto max-h-[calc(100dvh-13rem)] lg:max-h-[60vh]">
          <li v-for="conv in chatStore.conversations" :key="conv.id">
            <div
              class="group flex items-center gap-2 px-2 py-2 min-h-[44px] rounded-lg cursor-pointer text-sm transition active:bg-neutral-100 dark:active:bg-stone-800"
              :class="chatStore.conversationId === conv.id
                ? 'bg-accent-50 text-accent-700'
                : 'hover:bg-neutral-100 dark:hover:bg-stone-800 text-neutral-700 dark:text-neutral-300'"
              @click="switchConversation(conv.id)"
            >
              <div class="flex-1 min-w-0">
                <p class="truncate font-medium">{{ conv.title || conv.last_message || 'Untitled' }}</p>
                <p class="truncate text-xs text-neutral-400">{{ formatTime(conv.updated_at) }}</p>
              </div>
              <button
                class="shrink-0 w-8 h-8 flex items-center justify-center rounded-md text-neutral-400 opacity-70 lg:opacity-0 lg:group-hover:opacity-100 hover:text-red-500 active:text-red-500 transition"
                :title="$t('chat.deleteConversation') || 'Delete'"
                :aria-label="$t('chat.deleteConversation') || 'Delete'"
                @click.stop="removeConv(conv.id)"
              >
                ×
              </button>
            </div>
          </li>
        </ul>
      </div>
    </aside>

    <div class="flex flex-col min-w-0 flex-1 min-h-0">
    <h1 class="shrink-0 text-2xl lg:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-3 lg:mb-6">{{ $t('chat.title') }}</h1>

    <!-- Pet Selector -->
    <div class="shrink-0 bg-white dark:bg-stone-900 rounded-xl shadow-sm border p-3 lg:p-4 mb-3 lg:mb-6">
      <label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
        {{ $t('chat.selectPet') || 'Chatting for:' }}
      </label>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="pet in petStore.pets"
          :key="pet.id"
          class="px-4 py-2 rounded-lg border-2 transition text-sm font-medium"
          :class="selectedPetId === pet.id
            ? 'border-accent-500 bg-accent-50 text-accent-700'
            : 'border-neutral-200 dark:border-neutral-700/60 text-neutral-600 dark:text-neutral-400 dark:text-neutral-400 hover:border-neutral-300 dark:border-neutral-700'"
          @click="selectPet(pet.id)"
        >
<!-- eslint-disable-next-line vue/no-v-html -->
          <span v-html="petIcon(pet.breed)" /> {{ pet.name }}
        </button>
        <button
          v-if="petStore.pets.length === 0"
          class="px-4 py-2 rounded-lg border-2 border-dashed border-neutral-300 dark:border-neutral-700 text-neutral-400 dark:text-neutral-400 text-sm"
          disabled
        >
          {{ $t('chat.noPets') || 'No pets yet — create one first' }}
        </button>
      </div>
      <p v-if="selectedPetId" class="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 mt-2">
        {{ $t('chat.petContextHint') || 'AI will use this pet\'s profile for personalized recommendations' }}
      </p>
    </div>

    <!-- Chat Messages -->
    <div ref="chatContainer" class="bg-white dark:bg-stone-900 rounded-xl shadow-sm border p-3 sm:p-4 lg:p-6 mb-3 lg:mb-6 flex-1 min-h-0 overflow-y-auto overscroll-contain lg:flex-none lg:min-h-[400px] lg:max-h-[500px]">
      <div v-if="chatStore.messages.length === 0" class="text-center py-10 lg:py-16 text-neutral-400 dark:text-neutral-400">
<!-- eslint-disable-next-line vue/no-v-html -->
        <div class="text-5xl mb-4 text-accent-500/70" v-html="emptyStateIcon('chat')" />
        <p>{{ $t('chat.emptyHint') || 'Ask anything about pet care or product recommendations!' }}</p>
      </div>

      <div v-for="(msg, idx) in chatStore.messages" :key="idx" class="mb-4">
        <!-- User Message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="bg-accent-600 text-white rounded-lg px-4 py-2 max-w-[85%] sm:max-w-[75%] break-words">
            <p class="text-sm">{{ msg.content }}</p>
          </div>
        </div>

        <!-- AI Message with recommendations -->
        <div v-else class="flex gap-3">
          <div class="w-8 h-8 bg-accent-100 rounded-full flex items-center justify-center text-sm shrink-0">AI</div>
          <div class="flex-1 min-w-0 space-y-3 max-w-[calc(100%-2.75rem)] sm:max-w-[85%] break-words">
            <div class="bg-neutral-100 dark:bg-stone-800 rounded-lg px-4 py-2">
              <p class="text-sm text-neutral-800 dark:text-neutral-200">{{ msg.content }}</p>
            </div>

            <!-- Recommendation Cards -->
            <div v-if="msg.recommendations && msg.recommendations.length > 0" class="space-y-2">
              <p class="text-xs font-semibold text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wide">{{ $t('chat.recommendations') || 'Recommended Products' }}</p>
              <div
                v-for="rec in msg.recommendations"
                :key="rec.product_id || rec.id"
                class="flex items-center gap-3 p-3 bg-white dark:bg-stone-900 border rounded-lg cursor-pointer hover:border-accent-300 hover:shadow-sm transition"
                @click="navigateTo(localePath(`/products/${rec.slug || rec.product_id || rec.id}`))"
              >
                <img
                  v-if="rec.image"
                  :src="rec.image"
                  :alt="rec.product_name || rec.name"
                  class="w-12 h-12 rounded-md object-cover bg-neutral-100 dark:bg-stone-800 shrink-0"
                  loading="lazy"
                >
                <div
                  v-else
                  class="w-12 h-12 rounded-md bg-neutral-100 dark:bg-stone-800 shrink-0 flex items-center justify-center text-neutral-400 text-[10px]"
                >
                  {{ $t('chat.noImage') || 'No image' }}
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{{ rec.product_name || rec.name }}</p>
                  <p v-if="rec.reason" class="text-xs text-neutral-500 dark:text-neutral-400">{{ rec.reason }}</p>
                  <p v-if="rec.price" class="text-xs font-semibold text-accent-700 mt-0.5">{{ rec.price }}</p>
                </div>
                <div v-if="typeof rec.confidence === 'number'" class="text-end shrink-0">
                  <span class="text-xs px-2 py-0.5 bg-accent-100 text-accent-700 rounded-full font-medium">
                    {{ Math.round(rec.confidence * 100) }}% match
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="chatStore.loading" class="flex gap-3 mb-4">
        <div class="w-8 h-8 bg-accent-100 rounded-full flex items-center justify-center text-sm shrink-0">AI</div>
        <div class="bg-neutral-100 dark:bg-stone-800 rounded-lg px-4 py-3">
          <div class="flex gap-1">
            <div class="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style="animation-delay: 0ms" />
            <div class="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style="animation-delay: 150ms" />
            <div class="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style="animation-delay: 300ms" />
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area：移动端吸底 + safe-area 适配 -->
    <div class="shrink-0 -mx-3 sm:-mx-4 lg:mx-0 px-3 sm:px-4 lg:px-0 pt-2 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:pt-0 lg:pb-0 bg-neutral-50 dark:bg-stone-950 border-t border-neutral-200/70 dark:border-neutral-800 lg:border-t-0">
      <form class="flex gap-2 lg:gap-3" @submit.prevent="sendMsg">
        <input
          v-model="input"
          type="text"
          enterkeyhint="send"
          autocomplete="off"
          class="flex-1 min-w-0 px-3 lg:px-4 py-3 text-base border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-stone-900 rounded-lg focus:outline-none focus:ring-accent-500 focus:border-accent-500"
          :placeholder="$t('chat.placeholder') || 'Ask about your pet...'"
          :disabled="chatStore.loading"
        />
        <button
          type="submit"
          class="shrink-0 min-w-[76px] lg:min-w-0 px-4 lg:px-6 py-3 bg-accent-600 text-white rounded-lg hover:bg-accent-500 active:bg-accent-700 transition font-medium disabled:opacity-50"
          :disabled="!input.trim() || chatStore.loading"
        >
          {{ $t('chat.send') || 'Send' }}
        </button>
      </form>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { petIcon, emptyStateIcon } from '~/utils/iconSvgs'
import { usePetStore } from '~/stores/pet'
import { useChatStore } from '~/stores/chat'
const localePath = useLocalePath()

definePageMeta({
  middleware: 'auth',
})

const petStore = usePetStore()
const chatStore = useChatStore()

const chatContainer = ref<HTMLElement | null>(null)
const input = ref('')
const selectedPetId = ref<string | null>(null)
// 窄屏历史会话抽屉开关
const drawerOpen = ref(false)

function openDrawer() {
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && drawerOpen.value) closeDrawer()
}

watch(drawerOpen, (open) => {
  if (import.meta.client) {
    document.body.style.overflow = open ? 'hidden' : ''
  }
})



function selectPet(petId: string) {
  selectedPetId.value = petId
}

async function sendMsg() {
  const text = input.value.trim()
  if (!text || chatStore.loading) return

  input.value = ''
  await nextTick()
  scrollToBottom()

  await chatStore.sendMessage(text, selectedPetId.value || undefined)

  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function switchConversation(id: string) {
  closeDrawer()
  if (chatStore.conversationId === id) return
  await chatStore.setConversation(id)
  await nextTick()
  scrollToBottom()
}

function newChat() {
  closeDrawer()
  chatStore.newConversation()
  input.value = ''
}

async function removeConv(id: string) {
  await chatStore.removeConversation(id)
}

function formatTime(value?: string) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  petStore.loadPets()
  await chatStore.restoreSession()
  if (petStore.pets.length > 0) {
    selectedPetId.value = petStore.pets[0].id
  }
  await nextTick()
  scrollToBottom()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (import.meta.client) document.body.style.overflow = ''
})
</script>
