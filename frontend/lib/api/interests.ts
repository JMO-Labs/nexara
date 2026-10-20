/**
 * @file lib/api/interests.ts
 * @brief Interests API endpoints including admin analytics.
 */
import { apiGet } from "./client";

/**
 * @brief Interest analytics entry.
 */
export interface InterestAnalytics {
  category_slug: string;
  value: string;
  count: number;
}

/**
 * @brief Get interest analytics (admin only).
 * @return Array of InterestAnalytics
 */
export const getInterestAnalytics = () =>
  apiGet<InterestAnalytics[]>("/api/v1/interests/admin/interests/analytics");
