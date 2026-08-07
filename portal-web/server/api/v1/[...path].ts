import http from "node:http";
import https from "node:https";
import { defineEventHandler, readRawBody, setResponseStatus } from "h3";

export default defineEventHandler(async (event) => {
  const target = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
  const targetUrl = new URL(target);
  // Use event.path so trailing slashes are preserved (catch-all param strips them)
  const path = event.path;

  const body =
    event.method !== "GET" && event.method !== "HEAD"
      ? await readRawBody(event)
      : undefined;

  const headers: Record<string, string> = {};
  for (const [key, value] of Object.entries(
    Object.fromEntries(event.headers)
  )) {
    const lower = key.toLowerCase();
    if (["host", "connection", "transfer-encoding"].includes(lower)) continue;
    headers[key] = value;
  }
  if (body) {
    headers["content-length"] = String(Buffer.byteLength(body));
  }

  const result = await new Promise((resolve, reject) => {
    const mod = targetUrl.protocol === "https:" ? https : http;
    const req = mod.request(
      {
        hostname: targetUrl.hostname,
        port: targetUrl.port,
        path,
        method: event.method,
        headers,
        timeout: 30000,
      },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          setResponseStatus(
            event,
            res.statusCode || 200,
            res.statusMessage || ""
          );
          try {
            resolve(JSON.parse(data));
          } catch {
            resolve(data);
          }
        });
      }
    );
    req.on("timeout", () => {
      req.destroy();
      setResponseStatus(event, 504, "Gateway Timeout");
      reject(new Error("Upstream timeout"));
    });
    req.on("error", (err) => {
      console.error("[API Proxy] native http error:", err.message);
      setResponseStatus(event, 502, "Bad Gateway");
      reject(err);
    });
    if (body) req.write(body);
    req.end();
  });

  return result;
});
