/**
 * @file lib/api/adminAI.ts
 * @brief Admin AI configuration, metrics and connection-test endpoints.
 */
import { apiGet, apiPost, apiPut } from "./client";

export interface AIConfig {
  provider: string;
  sassybot_enabled: boolean;
  sass_level: number;
  probability: number;
  invoke_only: boolean;
  opt_out_count: number;
}

export type AIConfigUpdate = Partial<
  Omit<AIConfig, "provider" | "opt_out_count">
>;

export interface AIMetrics {
  daily_usage_cents: number;
  daily_budget_cents: number;
  last_7_days: { date: string; cents: number }[];
  breakdown: { feature: string; calls: number; cents: number }[];
}

export interface AIConnectionResult {
  success: boolean;
  message: string;
}

/** @brief Fetch current AI config. */
export const getAIConfig = () => apiGet<AIConfig>("/api/v1/admin/ai/config");

/** @brief Update Sassybot settings. @param body partial settings */
export const updateAIConfig = (body: AIConfigUpdate) =>
  apiPut<AIConfig>("/api/v1/admin/ai/config", body);

/** @brief Fetch usage metrics. */
export const getAIMetrics = () => apiGet<AIMetrics>("/api/v1/admin/ai/metrics");

/** @brief Probe the configured provider. */
export const testAIConnection = () =>
  apiPost<AIConnectionResult>("/api/v1/admin/ai/test-connection");
