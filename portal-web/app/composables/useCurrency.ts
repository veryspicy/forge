// Forge — Reactive Currency Composable
import { ref } from 'vue'

const currentCurrency = ref('USD')

export function useCurrency() {
  function formatPrice(amount: number, currency?: string): string {
    const code = currency || currentCurrency.value
    // Map currency codes to appropriate locales for correct formatting
    const localeMap: Record<string, string> = {
      USD: 'en-US',
      EUR: 'de-DE',
      GBP: 'en-GB',
      CNY: 'zh-CN',
      SAR: 'ar-SA',
    }
    const locale = localeMap[code] || 'en-US'
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: code,
    }).format(amount)
  }

  function setCurrency(code: string) {
    currentCurrency.value = code
  }

  return {
    currency: currentCurrency,
    formatPrice,
    setCurrency,
  }
}
