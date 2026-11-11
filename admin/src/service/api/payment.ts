import { get, post, put } from './helper';

/** 渠道可配置字段（与后端 payment_config_service.CredentialField 对齐） */
export interface PaymentChannelField {
  key: string;
  label: string;
  type: 'text' | 'secret' | 'select';
  required: boolean;
  placeholder: string;
  options: { label: string; value: string }[];
  help_text: string;
  /** 非敏感字段回显值；敏感字段恒为空 */
  value: string;
  /** 是否已保存过值（敏感字段仅回 masked） */
  saved: boolean;
  masked: string;
}

/** 单个支付渠道的运行期状态 */
export interface PaymentChannelState {
  channel: string;
  name: string;
  description: string;
  enabled: boolean;
  configured: boolean;
  fields: PaymentChannelField[];
  docs_url: string;
}

export interface PaymentConfigResponse {
  channels: PaymentChannelState[];
  enabled_channels: string[];
  note: string;
}

export interface TaxRuleItem {
  country: string;
  region: string;
  category: string;
  rate: string;
  name: string;
  applies_to_shipping: boolean;
}

export interface TaxConfig {
  provider: string;
  enabled: boolean;
  prices_include_tax: boolean;
  default_rate: string;
  rates: TaxRuleItem[];
}

export interface TaxProviderOption {
  value: string;
  label: string;
  description: string;
  available: boolean;
}

export interface TaxConfigResponse {
  config: TaxConfig;
  providers: TaxProviderOption[];
  defaults: TaxRuleItem[];
  note: string;
}

export interface TaxPreviewResponse {
  tax: number;
  rate: number;
  name: string;
  label: string;
  jurisdiction: string;
  taxable_amount: number;
  inclusive: boolean;
  total: number;
}

/** 清空某个已保存敏感值的哨兵值（与后端 CLEAR_SENTINEL 一致） */
export const CLEAR_SENTINEL = '__CLEAR__';

/** 支付渠道配置：启停 + 脱敏凭证 */
export function fetchPaymentConfig() {
  return get<PaymentConfigResponse>('/api/admin/v1/payment-config');
}

/** 整体保存启用渠道（顺序即 C 端按钮顺序） */
export function saveEnabledChannels(enabledChannels: string[]) {
  return put<{ enabled_channels: string[] }>('/api/admin/v1/payment-config/channels', {
    enabled_channels: enabledChannels
  });
}

/** 单渠道启停开关：保存后 C 端下一次请求即生效，无需重启/发布 */
export function togglePaymentChannel(channel: string, enabled: boolean) {
  return put<{ channel: string; enabled: boolean; enabled_channels: string[] }>(
    `/api/admin/v1/payment-config/${channel}/enabled`,
    { enabled }
  );
}

/** 保存渠道凭证（敏感字段加密落库，留空表示保留原值） */
export function savePaymentChannelCredentials(channel: string, values: Record<string, string>) {
  return put<{ channel: string; config: PaymentChannelState }>(`/api/admin/v1/payment-config/${channel}`, {
    values
  });
}

/** 连通性测试（只读探测，不产生扣款） */
export function testPaymentChannel(channel: string) {
  return post<{ channel: string; ok: boolean; message: string }>(`/api/admin/v1/payment-config/${channel}/test`);
}

/** 税费配置：静态税率表 + 引擎选择 */
export function fetchTaxConfig() {
  return get<TaxConfigResponse>('/api/admin/v1/tax-config');
}

/** 保存税率表（保存后立即生效） */
export function saveTaxConfig(config: TaxConfig) {
  return put<{ config: TaxConfig }>('/api/admin/v1/tax-config', config);
}

/** 计税预览（不落库） */
export function previewTax(payload: {
  country: string;
  region?: string | null;
  amount: string;
  shipping: string;
  category?: string | null;
}) {
  return post<TaxPreviewResponse>('/api/admin/v1/tax-config/preview', payload);
}
