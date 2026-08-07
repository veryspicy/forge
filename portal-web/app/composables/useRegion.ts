export interface RegionConfig {
  currency: string
  taxRate: number
  taxName: string
  paymentMethods: string[]
  shippingMethods: string[]
}

const regionConfigs: Record<string, RegionConfig> = {
  US: {
    currency: 'USD',
    taxRate: 0.08,
    taxName: 'Sales Tax',
    paymentMethods: ['stripe', 'paypal'],
    shippingMethods: ['usps', 'ups', 'fedex'],
  },
  DE: {
    currency: 'EUR',
    taxRate: 0.19,
    taxName: 'VAT',
    paymentMethods: ['stripe', 'paypal', 'klarna'],
    shippingMethods: ['dhl', 'dpd'],
  },
  FR: {
    currency: 'EUR',
    taxRate: 0.20,
    taxName: 'VAT',
    paymentMethods: ['stripe', 'paypal'],
    shippingMethods: ['colissimo', 'chronopost'],
  },
  SA: {
    currency: 'SAR',
    taxRate: 0.15,
    taxName: 'VAT',
    paymentMethods: ['stripe'],
    shippingMethods: ['aramex', 'dhl'],
  },
}

const localeMap: Record<string, string> = {
  US: 'en-US',
  DE: 'de-DE',
  FR: 'fr-FR',
  SA: 'ar-SA',
}

export function useRegion() {
  const runtimeConfig = useRuntimeConfig()

  const region = ref<string>(
    (runtimeConfig.public.region as string) || 'US',
  )
  const currency = ref<string>(
    (runtimeConfig.public.defaultCurrency as string) || 'USD',
  )

  const locale = computed<string>(() => localeMap[region.value] || 'en-US')

  const regionConfig = computed<RegionConfig>(
    () => regionConfigs[region.value] || regionConfigs.US,
  )

  function setRegion(code: string) {
    region.value = code
    currency.value = regionConfigs[code]?.currency || 'USD'
  }

  return {
    region,
    currency,
    locale,
    regionConfig,
    setRegion,
  }
}
