<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">{{ $t('chat.title') }}</h1>

    <!-- Pet Selector -->
    <div class="bg-white dark:bg-stone-900 rounded-xl shadow-sm border p-4 mb-6">
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
    <div ref="chatContainer" class="bg-white dark:bg-stone-900 rounded-xl shadow-sm border p-6 mb-6 min-h-[400px] max-h-[500px] overflow-y-auto">
      <div v-if="chatStore.messages.length === 0" class="text-center py-16 text-neutral-400 dark:text-neutral-400">
<!-- eslint-disable-next-line vue/no-v-html -->
        <div class="text-5xl mb-4 text-accent-500/70" v-html="emptyStateIcon('chat')" />
        <p>{{ $t('chat.emptyHint') || 'Ask anything about pet care or product recommendations!' }}</p>
      </div>

      <div v-for="(msg, idx) in chatStore.messages" :key="idx" class="mb-4">
        <!-- User Message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="bg-accent-600 text-white rounded-lg px-4 py-2 max-w-[75%]">
            <p class="text-sm">{{ msg.content }}</p>
          </div>
        </div>

        <!-- AI Message with recommendations -->
        <div v-else class="flex gap-3">
          <div class="w-8 h-8 bg-accent-100 rounded-full flex items-center justify-center text-sm shrink-0">AI</div>
          <div class="flex-1 space-y-3 max-w-[85%]">
            <div class="bg-neutral-100 dark:bg-stone-800 rounded-lg px-4 py-2">
              <p class="text-sm text-neutral-800 dark:text-neutral-200">{{ msg.content }}</p>
            </div>

            <!-- Recommendation Cards -->
            <div v-if="msg.recommendations && msg.recommendations.length > 0" class="space-y-2">
              <p class="text-xs font-semibold text-neutral-500 dark:text-neutral-400 dark:text-neutral-400 uppercase tracking-wide">{{ $t('chat.recommendations') || 'Recommended Products' }}</p>
              <div
                v-for="rec in msg.recommendations"
                :key="rec.product_id"
                class="flex items-center gap-3 p-3 bg-white dark:bg-stone-900 border rounded-lg cursor-pointer hover:border-accent-300 hover:shadow-sm transition"
                @click="navigateTo(localePath(`/products/${rec.slug || rec.product_id}`))"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{{ rec.product_name }}</p>
                  <p class="text-xs text-neutral-500 dark:text-neutral-400 dark:text-neutral-400">{{ rec.reason }}</p>
                </div>
                <div class="text-right shrink-0">
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

    <!-- Input Area -->
    <form class="flex gap-3" @submit.prevent="sendMsg">
      <input
        v-model="input"
        type="text"
        class="flex-1 px-4 py-3 border border-neutral-300 dark:border-neutral-700 rounded-lg focus:outline-none focus:ring-accent-500 focus:border-accent-500"
        :placeholder="$t('chat.placeholder') || 'Ask about your pet...'"
        :disabled="chatStore.loading"
      />
      <button
        type="submit"
        class="px-6 py-3 bg-accent-600 text-white rounded-lg hover:bg-accent-500 transition font-medium disabled:opacity-50"
        :disabled="!input.trim() || chatStore.loading"
      >
        {{ $t('chat.send') || 'Send' }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
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

onMounted(() => {
  petStore.loadPets()
  chatStore.loadConversations()
  if (petStore.pets.length > 0) {
    selectedPetId.value = petStore.pets[0].id
  }
})
</script>
