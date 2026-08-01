/**
 * 站点配置 composable — 从 /api/v1/site-config 读取品牌 / 主题等配置
 */
import { ref, onMounted } from 'vue'

interface BrandConfig {
  logo_url: string
  site_name: string
  primary_color: string
  secondary_color: string
}

export function useSiteConfig() {
  const brand = ref<BrandConfig>({
    logo_url: '',
    site_name: 'Forge',
    primary_color: '#4f46e5',
    secondary_color: '#ec4899',
  })
  const loading = ref(false)

  async function fetchConfig() {
    loading.value = true
    try {
      const res = await $fetch<{ brand: BrandConfig }>('/api/v1/site-config')
      if (res?.brand) {
        brand.value = { ...brand.value, ...res.brand }
      }
    } catch {
      // 静默降级，使用默认值
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    fetchConfig()
  })

  return { brand, loading, fetchConfig }
}
