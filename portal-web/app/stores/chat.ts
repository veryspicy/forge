// Forge — Chat Store
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

interface ChatRecommendation {
  product_id?: string | number;
  product_name?: string;
  confidence?: number;
  reason?: string;
  id?: string | number;
  name?: string;
  price?: string;
  image?: string | null;
  slug?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  recommendations?: ChatRecommendation[];
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  last_message: string;
  updated_at: string;
}

export const useChatStore = defineStore("chat", () => {
  const messages = ref<ChatMessage[]>([]);
  const conversations = ref<Conversation[]>([]);
  const conversationId = ref<string | null>(null);
  const loading = ref(false);
  const isStreaming = ref(false);
  const streamedContent = ref("");

  const { aiChat, fetchConversations, fetchConversation, deleteConversation } = useApi();

  // 本地会话快照：刷新 / 重新登录后据此恢复上次对话
  const STORAGE_KEY = "forge_chat_session";

  function persist() {
    if (!import.meta.client) return;
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          conversationId: conversationId.value,
          messages: messages.value,
        }),
      );
    } catch {
      /* ignore */
    }
  }

  function clearPersisted() {
    if (!import.meta.client) return;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }

  const loadMessages = async (id: string) => {
    loading.value = true;
    try {
      const result: any = await fetchConversation(id);
      const items: any[] = result?.items || [];
      messages.value = items
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({
          id: String(m.id),
          role: m.role as "user" | "assistant",
          content: m.content || "",
          recommendations: m.recommendations || [],
          timestamp: m.created_at || new Date().toISOString(),
        }));
      conversationId.value = id;
      persist();
    } catch {
      /* ignore */
    } finally {
      loading.value = false;
    }
  };

  /** 进入聊天页时恢复：会话列表 + 上次打开的对话内容 */
  const restoreSession = async () => {
    await loadConversations();
    if (conversationId.value) {
      await loadMessages(conversationId.value);
      return;
    }
    if (!import.meta.client) return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved?.conversationId) {
        await loadMessages(saved.conversationId);
      } else if (Array.isArray(saved?.messages) && saved.messages.length) {
        messages.value = saved.messages;
      }
    } catch {
      /* ignore */
    }
  };

  const sendMessage = async (content: string, petId?: string) => {
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    messages.value.push(userMsg);
    persist();

    loading.value = true;
    isStreaming.value = true;
    streamedContent.value = "";

    try {
      const result: any = await aiChat({
        message: content,
        conversation_id: conversationId.value || undefined,
        pet_id: petId,
      });

      conversationId.value = result.conversation_id;

      const aiMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: result.response || result.content || "",
        recommendations: result.recommendations || [],
        timestamp: new Date().toISOString(),
      };
      messages.value.push(aiMsg);
      persist();

      await loadConversations();
    } catch {
      // 预览模式或网络失败时静默，避免红屏
      messages.value.push({
        id: `a-${Date.now()}`,
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      });
    } finally {
      loading.value = false;
      isStreaming.value = false;
    }
  };

  const loadConversations = async () => {
    try {
      const result: any = await fetchConversations();
      conversations.value = result.items || result || [];
    } catch {
      /* ignore */
    }
  };

  const removeConversation = async (id: string) => {
    await deleteConversation(id);
    conversations.value = conversations.value.filter((c) => c.id !== id);
    if (conversationId.value === id) {
      conversationId.value = null;
      messages.value = [];
      clearPersisted();
    }
  };

  const newConversation = () => {
    conversationId.value = null;
    messages.value = [];
    streamedContent.value = "";
    clearPersisted();
  };

  const setConversation = async (id: string) => {
    await loadMessages(id);
  };

  return {
    messages,
    conversations,
    conversationId,
    loading,
    isStreaming,
    streamedContent,
    sendMessage,
    loadConversations,
    loadMessages,
    restoreSession,
    removeConversation,
    deleteConversation: removeConversation,
    newConversation,
    setConversation,
  };
});

// Persist: enable pinia-plugin-persistedstate in nuxt.config.ts to auto-persist conversations to localStorage

