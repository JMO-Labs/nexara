/**
 * @file lib/api/retention.ts
 * @brief Admin retention policy endpoints.
 */
import { apiGet, apiPut, seg } from "./client";
import type {
  RetentionPolicy,
  RetentionUpdate,
} from "@/lib/retention-policies";

/** @brief List all retention policies. */
export const listRetentionPolicies = () =>
  apiGet<RetentionPolicy[]>("/api/v1/admin/retention");

/**
 * @brief Update one policy.
 * @param key policy_key
 * @param body enabled, retention_days, delete_media_files
 */
export const updateRetentionPolicy = (key: string, body: RetentionUpdate) =>
  apiPut<RetentionPolicy>(`/api/v1/admin/retention/${seg(key)}`, body);
