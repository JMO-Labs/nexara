"use client";
/**
 * @file hooks/useFeature.ts
 * @brief Read one per-community feature flag. While loading, default-on keys
 *        read true (no flicker) and reply_by_email reads false.
 */
import { useQuery } from "@tanstack/react-query";
import { getFeatures, type FeatureKey } from "@/lib/api/features";

/** @brief Query key shared with the admin Features tab. */
export const FEATURES_KEY = ["features"] as const;

/**
 * @param key feature flag key
 * @return whether the feature is on for this community
 */
export function useFeature(key: FeatureKey): boolean {
  const { data } = useQuery({
    queryKey: FEATURES_KEY,
    queryFn: getFeatures,
    staleTime: 5 * 60_000,
  });
  return data ? data[key] : key !== "reply_by_email";
}
