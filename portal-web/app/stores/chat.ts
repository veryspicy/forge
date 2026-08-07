// Forge — Chat Store
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  recommendations?: any[];
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

  const { aiChat, fetchConversations, deleteConversation } = useApi();

  const sendMessage = async (content: string, petId?: string) => {
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    messages.value.push(userMsg);

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

      await loadConversations();
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
    }
  };

  const newConversation = () => {
    conversationId.value = null;
    messages.value = [];
    streamedContent.value = "";
  };

  const setConversation = (id: string) => {
    conversationId.value = id;
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
    removeConversation,
    deleteConversation: removeConversation,
    newConversation,
    setConversation,
  };
});

// Persist: enable pinia-plugin-persistedstate in nuxt.config.ts to auto-persist conversations to localStorage

