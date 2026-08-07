import { ref } from 'vue'

interface ToastItem {
  id: number
  message: string
  type: 'success' | 'error'
}

const toasts = ref<ToastItem[]>([])
let nextId = 0

export function useToast() {
  function show(message: string, type: 'success' | 'error') {
    const id = nextId++
    toasts.value.push({ id, message, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 4000)
  }

  return {
    toasts,
    toast: {
      success(msg: string) { show(msg, 'success') },
      error(msg: string) { show(msg, 'error') },
    },
  }
}

// Global singleton for non-composable imports
const globalInstance = useToast()
export const toast = globalInstance.toast
