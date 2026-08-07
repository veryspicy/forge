<template>
  <div class="fixed bottom-4 right-4 z-40">
    <!-- Toggle Button -->
    <button
      class="w-14 h-14 rounded-full bg-primary-600 text-white shadow-lg hover:bg-primary-700 transition flex items-center justify-center"
      @click="open = !open"
    >
      <svg v-if="!open" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
      </svg>
      <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </button>

    <!-- Chat Panel -->
    <Transition name="widget">
      <div
        v-if="open"
        class="absolute bottom-16 right-0 w-80 bg-white rounded-2xl shadow-2xl border overflow-hidden"
      >
        <!-- Header -->
        <div class="bg-primary-600 text-white px-4 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-lg">🐾</span>
            <span class="font-semibold text-sm">{{ $t('chat.title') }}</span>
          </div>
          <button class="text-white/80 hover:text-white transition" @click="open = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <!-- Messages -->
        <div class="h-64 overflow-y-auto p-3 space-y-3">
          <div v-if="messages.length === 0" class="text-center py-8">
            <p class="text-sm text-gray-400">{{ $t('chat.welcomeHint') }}</p>
          </div>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] px-3 py-2 rounded-xl text-xs"
              :class="
                msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-700 rounded-bl-sm'
              "
            >
              {{ msg.content }}
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="border-t p-3 flex gap-2">
          <input
            v-model="input"
            type="text"
            class="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary-400"
            :placeholder="$t('chat.placeholder')"
            @keydown.enter="send"
          />
          <button
            class="px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition"
            @click="send"
          >
            {{ $t('chat.send') }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const open = ref(false)
const input = ref('')

interface Msg {
  role: 'user' | 'assistant'
  content: string
}

const messages = ref<Msg[]>([])

function send() {
  const text = input.value.trim()
  if (!text) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  setTimeout(() => {
    messages.value.push({ role: 'assistant', content: 'I\'m here to help with your pet care questions!' })
  }, 800)
}
</script>

<style scoped>
.widget-enter-active {
  transition: all 0.2s ease-out;
}
.widget-leave-active {
  transition: all 0.15s ease-in;
}
.widget-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
.widget-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
</style>
