// Nuxt 3 配置
// https://nuxt.com/docs/api/configuration/nuxt-config

import tailwindcss from "@tailwindcss/vite";

export default defineNuxtConfig({
  srcDir: "app",
  css: ["~/assets/css/main.css"],

  devtools: { enabled: true },

  devServer: {
    port: 3000,
  },

  imports: {
    dirs: ["composables", "stores"],
  },

  typescript: {
    shim: false,
    typeCheck: true,
    tsConfig: {
      compilerOptions: {
        paths: {
          "~": ["./app"],
          "~/*": ["./app/*"],
          "@": ["./app"],
          "@/*": ["./app/*"],
        },
      },
    },
  },

  vite: {
    plugins: [tailwindcss() as any],
  },

  // 区域配置
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "/api/v1",
      aiChatBase: process.env.NUXT_PUBLIC_AI_CHAT_BASE || "http://192.168.1.8:8001",
      region: process.env.NUXT_PUBLIC_REGION || "na", // na | eu | me
      defaultCurrency: process.env.NUXT_PUBLIC_DEFAULT_CURRENCY || "USD",
      stripePublicKey: process.env.NUXT_PUBLIC_STRIPE_KEY || "",
    },
  },

  // 模块
  modules: ["@pinia/nuxt", "@nuxt/image", "@nuxtjs/i18n"],

  // i18n 配置
  i18n: {
    langDir: "locales",
    strategy: "prefix",
    defaultLocale: "en",
    vueI18n: "./i18n.config.ts",
    locales: [
      { code: "en", name: "English", file: "en.json" },
      { code: "zh", name: "中文", file: "zh.json" },
      { code: "ar", name: "العربية", file: "ar.json", dir: "rtl" },
      { code: "de", name: "Deutsch", file: "de.json" },
      { code: "fr", name: "Français", file: "fr.json" },
    ],
    bundle: {
      optimizeTranslationDirective: false,
    },
    lazy: false,
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: "forge_locale",
    },
  },

  // 生产环境配置
  nitro: {
    compressPublicAssets: { brotli: true },
  },

  // 安全头
  app: {
    head: {
      meta: [
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        { name: "description", content: "AI-Powered Pet Supplies Store" },
      ],
    },
  },

  compatibilityDate: "2025-01-01",
});
