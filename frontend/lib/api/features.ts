/**
 * @file lib/api/features.ts
 * @brief Per-community feature flags (member read, admin write).
 */
import { apiGet, apiPut } from "./client";

export const FEATURE_KEYS = [
  "recap",
  "on_this_day",
  "daily_question",
  "time_capsules",
  "event_albums",
  "recipes",
  "memorials",
  "expenses",
  "rides",
  "chores",
  "relations",
  "family_tree",
  "reconnect_nudges",
  "safe_arrival",
  "voice_stories",
  "simple_mode",
  "newsletter",
  "reply_by_email",
  "nsfw",
] as const;

export type FeatureKey = (typeof FEATURE_KEYS)[number];
export type Features = Record<FeatureKey, boolean>;

/** @brief Effective flags for the signed-in member. */
export const getFeatures = () => apiGet<Features>("/api/v1/features");
/** @brief Admin: change some flags; returns the effective flags. */
export const putFeatures = (patch: Partial<Features>) =>
  apiPut<Features>("/api/v1/admin/features", patch);
