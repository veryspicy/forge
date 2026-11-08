// Nuxt 3 配置
// https://nuxt.com/docs/api/configuration/nuxt-config

import tailwindcss from "@tailwindcss/vite";
import type { LocaleObject } from "@nuxtjs/i18n";

// 构建期支持的语言清单（与运行期「站点生效语言」分离，后者由后端站点配置派生）
import { PORTAL_DEFAULT_LOCALE, PORTAL_LOCALES } from "./app/utils/i18n-config";

// 容器内 routeRules/devProxy 的 backend 代理目标（compose 注入 NUXT_BACKEND_URL=http://backend:8000；
// 本地开发未注入时回退 127.0.0.1:8000）
const backendUrl = process.env.NUXT_BACKEND_URL || "http://127.0.0.1:8000";

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
      adminApiBase: process.env.NUXT_PUBLIC_ADMIN_API_BASE || "http://localhost:8000/api/admin/v1",
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
    defaultLocale: PORTAL_DEFAULT_LOCALE,
    vueI18n: "./i18n.config.ts",
    // 构建期支持全集；站点生效语言由 site_profiles.config.i18n 运行期派生（locale-guard 拦截未生效前缀）
    locales: PORTAL_LOCALES as unknown as LocaleObject[],
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
    // 代理上传图片到后端（C-end 预览/开发模式加载 MinIO/本地图片）
    // （/api/v1 由 app/server/api/v1/[...path].ts 处理）
    routeRules: {
      "/api/images/**": {
        proxy: { to: `${backendUrl}/api/images/**` },
      },
      // /minio/**、/uploads/** 由 server/routes/*/[...path].ts 流式代理处理
      // （routeRules 通配替换在 dev/prod 均存在路径改写风险，弃用；devProxy 与 server route 并存时 Nuxt 优先 devProxy，一并移除）
    },
  },

  // 安全头
  app: {
    head: {
      meta: [
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        { name: "description", content: "AI-Powered Pet Supplies Store" },
      ],
      link: [],
      script: [
        {
          // Dark theme bootstrap — prevents FOUC before Nuxt hydrates
          innerHTML:
            "(function(){try{var t=localStorage.getItem('forge-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})();",
          tagPosition: "head",
        },
      ],
    },
  },

  compatibilityDate: "2025-01-01",
});
