// Admin API composable — wraps /api/admin/v1 endpoints
import type { $Fetch } from "nitropack";

const ADMIN_BASE = "http://localhost:8000/api/admin/v1";

let _fetch: $Fetch | null = null;

function getFetch(): $Fetch {
  if (!_fetch) {
    const { token } = useAuth();
    _fetch = $fetch.create({
      baseURL: ADMIN_BASE,
      onRequest({ options }) {
        if (token.value) {
          options.headers = new Headers(options.headers);
          options.headers.set("Authorization", `Bearer ${token.value}`);
        }
      },
      onResponseError({ response }) {
        const msg = response._data?.detail || response._data?.message || "Request failed";
        console.error(`[Admin API] ${response.status}: ${msg}`);
      },
    });
  }
  return _fetch;
}

async function apiGet<T = any>(path: string, params?: Record<string, any>): Promise<T> {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return getFetch()(`${path}${query}`);
}

async function apiPost<T = any>(path: string, data?: any): Promise<T> {
  return getFetch()(path, { method: "POST", body: data });
}

async function apiPatch<T = any>(path: string, data?: any): Promise<T> {
  return getFetch()(path, { method: "PATCH", body: data });
}

async function apiDelete<T = any>(path: string): Promise<T> {
  return getFetch()(path, { method: "DELETE" });
}

// Dashboard
export function getDashboardStats() {
  return apiGet("/dashboard/stats");
}

// Products
export function getProducts(params?: Record<string, any>) {
  return apiGet("/products", params);
}

export function createProduct(data: any) {
  return apiPost("/products", data);
}

export function updateProduct(id: string, data: any) {
  return apiPatch(`/products/${id}`, data);
}

export function deleteProduct(id: string) {
  return apiDelete(`/products/${id}`);
}

export function uploadProductImage(productId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { token } = useAuth();
  return $fetch(`${ADMIN_BASE}/products/${productId}/upload-image`, {
    method: "POST",
    body: formData,
    headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
  });
}

// Orders
export function getOrders(params?: Record<string, any>) {
  return apiGet("/orders", params);
}

export function approveOrder(id: string) {
  return apiPost(`/orders/${id}/approve`);
}

export function rejectOrder(id: string, reason?: string) {
  return apiPost(`/orders/${id}/reject`, { reason });
}

export function startProcurement(id: string) {
  return apiPost(`/orders/${id}/procure`);
}

// Suppliers
export function getSuppliers(params?: Record<string, any>) {
  return apiGet("/suppliers", params);
}

export function createSupplier(data: any) {
  return apiPost("/suppliers", data);
}

export function deactivateSupplier(id: string) {
  return apiPost(`/suppliers/${id}/deactivate`);
}

// Pricing
export function getPricingRules() {
  return apiGet("/pricing");
}

export function createPricingRule(data: any) {
  return apiPost("/pricing/rules", data);
}

export function createPromotion(data: any) {
  return apiPost("/pricing/promotions", data);
}

// Chat
export function getChatRequests() {
  return apiGet("/chat-requests");
}

// Settings
export function getSettings() {
  return apiGet("/settings");
}

export function updateSettings(data: any) {
  return apiPatch("/settings", data);
}

// AI Probe
export function probeProducts(data: any) {
  return apiPost("/probe", data);
}
