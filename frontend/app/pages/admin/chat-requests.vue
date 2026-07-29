<template>
  <div class="flex h-[calc(100vh-7rem)] gap-0 overflow-hidden rounded-lg border border-neutral-200 bg-white">
    <!-- Left: Request List -->
    <aside class="flex w-[360px] shrink-0 flex-col border-r border-neutral-200">
      <!-- Search -->
      <div class="border-b border-neutral-200 px-4 py-3">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索用户名或消息..."
          class="w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-sm text-neutral-800 placeholder-neutral-400 outline-none transition focus:border-accent-400 focus:ring-1 focus:ring-accent-400"
        />
      </div>

      <!-- List -->
      <div class="flex-1 overflow-y-auto">
        <!-- Loading skeleton -->
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="flex items-center gap-3 border-b border-neutral-100 px-4 py-3">
            <div class="size-10 shrink-0 animate-pulse rounded-full bg-neutral-100" />
            <div class="min-w-0 flex-1 space-y-1.5">
              <div class="h-3.5 w-24 animate-pulse rounded bg-neutral-100" />
              <div class="h-3 w-40 animate-pulse rounded bg-neutral-100" />
            </div>
          </div>
        </template>

        <!-- Empty -->
        <div v-else-if="filteredRequests.length === 0" class="flex flex-col items-center justify-center py-16 text-neutral-400">
          <svg class="mb-3 size-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <p class="text-sm">暂无客服请求</p>
        </div>

        <!-- Request items -->
        <button
          v-for="req in filteredRequests"
          :key="req.id"
          :class="[
            'flex w-full items-start gap-3 border-b border-neutral-100 px-4 py-3 text-left transition',
            selectedId === req.id
              ? 'bg-accent-50 border-l-2 border-l-accent-500'
              : 'hover:bg-neutral-50',
          ]"
          @click="selectRequest(req)"
        >
          <!-- Avatar -->
          <span
            :class="[
              'flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-bold',
              selectedId === req.id
                ? 'bg-accent-500 text-white'
                : 'bg-neutral-200 text-neutral-600',
            ]"
          >
            {{ (req.user_name ?? req.user_id ?? '?')[0].toUpperCase() }}
          </span>
          <!-- Info -->
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <span class="truncate text-sm font-medium text-neutral-800">
                {{ req.user_name ?? req.user_id }}
              </span>
              <span class="shrink-0 text-[11px] text-neutral-400">
                {{ formatTime(req.last_message_at ?? req.created_at) }}
              </span>
            </div>
            <p class="mt-0.5 truncate text-xs text-neutral-500">
              {{ req.last_message ?? req.subject ?? '' }}
            </p>
            <div class="mt-1.5">
              <ChatStatusBadge :status="req.status" />
            </div>
          </div>
        </button>
      </div>
    </aside>

    <!-- Right: Detail Panel -->
    <div class="flex flex-1 flex-col">
      <!-- Empty state -->
      <template v-if="!selectedRequest">
        <div class="flex flex-1 flex-col items-center justify-center text-neutral-400">
          <svg class="mb-3 size-12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 0 1-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p class="text-sm">选择左侧对话查看详情</p>
        </div>
      </template>

      <!-- Conversation view -->
      <template v-else>
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-neutral-200 px-5 py-3">
          <div class="flex items-center gap-3">
            <span class="flex size-9 items-center justify-center rounded-full bg-accent-500 text-sm font-bold text-white">
              {{ selectedInitial }}
            </span>
            <div>
              <p class="text-sm font-medium text-neutral-800">
                {{ selectedRequest.user_name ?? selectedRequest.user_id }}
              </p>
              <p class="text-xs text-neutral-400">{{ selectedRequest.id }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <ChatStatusBadge :status="selectedRequest.status" />
            <button
              class="rounded-md px-3 py-1.5 text-xs font-medium text-green-700 transition hover:bg-green-50"
              @click="markResolved"
            >
              标记已解决
            </button>
          </div>
        </div>

        <!-- Messages -->
        <div ref="messageContainer" class="flex-1 overflow-y-auto px-5 py-4">
          <div v-for="(msg, idx) in selectedRequest.messages ?? []" :key="idx" class="mb-4">
            <!-- User message (right aligned) -->
            <div v-if="msg.role === 'user'" class="flex justify-end">
              <div class="max-w-[70%] rounded-2xl rounded-br-md bg-neutral-100 px-4 py-2.5">
                <p class="text-sm text-neutral-800 whitespace-pre-wrap">{{ msg.content }}</p>
                <p class="mt-1 text-right text-[11px] text-neutral-400">
                  {{ formatTime(msg.timestamp ?? msg.created_at) }}
                </p>
              </div>
            </div>

            <!-- AI / human reply (left aligned) -->
            <div v-else class="flex items-start gap-2">
              <span
                :class="[
                  'flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold',
                  msg.role === 'human'
                    ? 'bg-indigo-100 text-indigo-600'
                    : 'bg-accent-100 text-accent-600',
                ]"
              >
                {{ msg.role === 'human' ? 'H' : 'AI' }}
              </span>
              <div class="max-w-[70%] rounded-2xl rounded-bl-md bg-white border border-neutral-200 px-4 py-2.5">
                <p class="text-sm text-neutral-800 whitespace-pre-wrap">{{ msg.content }}</p>
                <p class="mt-1 text-[11px] text-neutral-400">
                  {{ formatTime(msg.timestamp ?? msg.created_at) }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Action bar -->
        <div class="border-t border-neutral-200 px-5 py-3">
          <!-- Not in takeover -->
          <template v-if="!isTakeover">
            <button
              class="w-full rounded-md bg-accent-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-700 active:bg-accent-800"
              @click="startTakeover"
            >
              接管对话
            </button>
          </template>

          <!-- In takeover mode -->
          <template v-else>
            <div class="flex items-center gap-2">
              <div class="relative flex-1">
                <input
                  v-model="takeoverMessage"
                  type="text"
                  placeholder="输入人工回复..."
                  :class="[
                    'w-full rounded-lg border-2 px-4 py-2.5 pr-12 text-sm transition',
                    takeoverMessage.trim()
                      ? 'border-indigo-400 bg-indigo-50 text-neutral-800 placeholder-indigo-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                      : 'border-amber-400 bg-amber-50 text-neutral-800 placeholder-amber-300 focus:border-amber-500 focus:ring-2 focus:ring-amber-200',
                  ]"
                  @keyup.enter="sendTakeoverMessage"
                />
                <button
                  class="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md bg-indigo-500 px-3 py-1 text-xs font-medium text-white transition hover:bg-indigo-600 disabled:opacity-40"
                  :disabled="!takeoverMessage.trim()"
                  @click="sendTakeoverMessage"
                >
                  发送
                </button>
              </div>
              <button
                class="shrink-0 rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm font-medium text-neutral-600 transition hover:bg-neutral-50"
                @click="endTakeover"
              >
                结束接管
              </button>
            </div>
          </template>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getChatRequests } from "~/composables/useAdminApi";

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
})

interface ChatMessage {
  role: "user" | "ai" | "human";
  content: string;
  timestamp?: string;
  created_at?: string;
}

interface ChatRequest {
  id: string;
  user_id?: string;
  user_name?: string;
  status: string;
  subject?: string;
  last_message?: string;
  last_message_at?: string;
  created_at?: string;
  messages?: ChatMessage[];
}

const loading = ref(true);
const requests = ref<ChatRequest[]>([]);
const selectedId = ref<string | null>(null);
const searchQuery = ref("");
const isTakeover = ref(false);
const takeoverMessage = ref("");
const messageContainer = ref<HTMLElement | null>(null);

const selectedRequest = computed<ChatRequest | null>(() => {
  return requests.value.find((r) => r.id === selectedId.value) ?? null;
});

const selectedInitial = computed(() => {
  const r = selectedRequest.value;
  return (r?.user_name ?? r?.user_id ?? "?")[0].toUpperCase();
});

const filteredRequests = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return requests.value;
  return requests.value.filter((r) => {
    const name = (r.user_name ?? r.user_id ?? "").toLowerCase();
    const msg = (r.last_message ?? r.subject ?? "").toLowerCase();
    return name.includes(q) || msg.includes(q);
  });
});

async function fetchRequests() {
  loading.value = true;
  try {
    const data = await getChatRequests() as any;
    requests.value = Array.isArray(data) ? data : (data?.data ?? []);
  } catch {
    requests.value = [];
  } finally {
    loading.value = false;
  }
}

function selectRequest(req: ChatRequest) {
  selectedId.value = req.id;
  isTakeover.value = false;
  takeoverMessage.value = "";
  nextTick(() => scrollToBottom());
}

function formatTime(ts?: string): string {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return "刚刚";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return ts;
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = messageContainer.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

function startTakeover() {
  isTakeover.value = true;
  takeoverMessage.value = "";
  nextTick(() => scrollToBottom());
}

function endTakeover() {
  isTakeover.value = false;
  takeoverMessage.value = "";
}

function sendTakeoverMessage() {
  const content = takeoverMessage.value.trim();
  if (!content || !selectedRequest.value) return;

  const msg: ChatMessage = {
    role: "human",
    content,
    timestamp: new Date().toISOString(),
  };
  if (!selectedRequest.value.messages) {
    selectedRequest.value.messages = [];
  }
  selectedRequest.value.messages.push(msg);
  takeoverMessage.value = "";
  nextTick(() => scrollToBottom());
}

function markResolved() {
  if (!selectedRequest.value) return;
  selectedRequest.value.status = "resolved";
}

onMounted(() => {
  fetchRequests();
});
</script>
