/**
 * @file lib/api/storage.ts
 * @brief Per-user storage quota endpoint.
 */
import { apiGet } from "./client";

export interface StorageUsage {
  used_bytes: number;
  quota_bytes: number;
  by_type: {
    photos: number;
    videos: number;
    documents: number;
    other: number;
  };
}

/**
 * @brief Fetch storage usage for a user.
 * @param userId user id
 * @return usage payload
 */
export const getStorage = (userId: string) =>
  apiGet<StorageUsage>(`/users/${userId}/storage`);
