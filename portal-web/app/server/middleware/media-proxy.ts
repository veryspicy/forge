// Forge — /minio/** 与 /uploads/** 图片流式代理
// 背景：nuxt.config routeRules proxy 的通配替换会改写 bucket 路径导致 backend 404；
//       本仓库 nitro server 目录为 app/server（srcDir=app），server/middleware 全局短路代理
//       dev 与 prod 构建均加载，行为一致。
import { defineEventHandler, proxyRequest } from "h3";

export default defineEventHandler(async (event) => {
  const p = event.path || "";
  if (!p.startsWith("/minio/") && !p.startsWith("/uploads/")) {
    return;
  }
  const target =
    process.env.NUXT_BACKEND_URL ||
    process.env.API_PROXY_TARGET ||
    "http://127.0.0.1:8000";
  return proxyRequest(event, `${target}${p}`);
});
