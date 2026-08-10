import process from 'node:process';
import { URL, fileURLToPath } from 'node:url';
import { defineConfig, loadEnv } from 'vite';
import { setupVitePlugins } from './build/plugins';
import { createViteProxy, getBuildTime } from './build/config';

export default defineConfig(configEnv => {
  const viteEnv = loadEnv(configEnv.mode, process.cwd()) as unknown as Env.ImportMeta;

  const buildTime = getBuildTime();

  const enableProxy = configEnv.command === 'serve' && !configEnv.isPreview;

  return {
    base: viteEnv.VITE_BASE_URL,
    resolve: {
      alias: {
        '~': fileURLToPath(new URL('./', import.meta.url)),
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
          additionalData: `@use "@/styles/scss/global.scss" as *;`
        }
      }
    },
    plugins: setupVitePlugins(viteEnv, buildTime),
    define: {
      BUILD_TIME: JSON.stringify(buildTime)
    },
    server: {
      host: '0.0.0.0',
      port: 8383,
      open: true,
      proxy: {
        ...createViteProxy(viteEnv, enableProxy),
        // 注意：代理项按声明顺序匹配，越具体越前置。
        // 1) C 端公共接口（Nuxt 加载 iframe 后，其 axios fetch baseURL=/api 会走 admin 域）：
        //    /api/v1/* 对应 backend 中 include_router(public_*_router, prefix="/api/v1")
        //    必须放在 '/api/admin/v1/*' （由 createViteProxy 注入）之后但通常 createViteProxy
        //    展开后在当前 proxy 对象之前；由于 JS 对象 key 遍历按插入顺序，这里显式确保
        //    createViteProxy() 先展开含 admin 前缀（更长），其后再写公共 /api/v1 前缀。
        '/api/v1': {
          target: viteEnv.VITE_SERVICE_BASE_URL || 'http://127.0.0.1:8000',
          changeOrigin: true
        },
        // 2) 预览 iframe 页面根路径（走 Nuxt 3000 本地）
        '/portal-preview': {
          target: 'http://localhost:3000',
          changeOrigin: true,
          rewrite: path => path.replace(/^\/portal-preview/, '')
        },
        // 3) C 端 i18n 语言前缀路由（/zh/*、/en/*、/ar/* 及裸路径 /zh、/en、/ar）：
        //    点 iframe 内导航链接后，Nuxt 会把 iframe URL 更新到 8383/zh/products 这类不带
        //    /portal-preview 前缀的路径；此时若用户刷新或服务端渲染触发再次 GET，admin Vite
        //    必须把这些 C 端语言路由转发到 3000，否则会落到 admin 的 404 页面。
        '/zh': {
          target: 'http://localhost:3000',
          changeOrigin: true
        },
        '/en': {
          target: 'http://localhost:3000',
          changeOrigin: true
        },
        '/ar': {
          target: 'http://localhost:3000',
          changeOrigin: true
        },
        // 4) Nuxt 内部绝对资源：/_nuxt/* 构建产物与 /favicon.ico
        '/_nuxt': {
          target: 'http://localhost:3000',
          changeOrigin: true
        },
        // 5) NuxtImage /_ipx/* 图片处理路由（C 端 Nuxt 会用绝对路径请求）
        '/_ipx': {
          target: 'http://localhost:3000',
          changeOrigin: true
        },
        '/favicon.ico': {
          target: 'http://localhost:3000',
          changeOrigin: true
        }
      }
    },
    preview: {
      port: 9725
    },
    build: {
      reportCompressedSize: false,
      sourcemap: viteEnv.VITE_SOURCE_MAP === 'Y',
      commonjsOptions: {
        ignoreTryCatch: false
      }
    }
  };
});
