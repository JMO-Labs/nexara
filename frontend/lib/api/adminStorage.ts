/**
 * @file lib/api/adminStorage.ts
 * @brief Admin storage analytics API.
 */
import { apiGet } from "./client";

export interface StorageCurrent {
  total_bytes: number;
  by_category: Record<string, number>;
}
export interface StorageSnapshot {
  date: string;
  total_bytes: number;
}
export interface UserStorage {
  user_id: string;
  display_name: string;
  used_bytes: number;
  percent_of_total: number;
}
export interface StorageResponse {
  current: StorageCurrent;
  snapshots: StorageSnapshot[];
  per_user: UserStorage[];
}
export interface UserStoragePage {
  items: UserStorage[];
  total: number;
  page: number;
  page_size: number;
}

/** @brief Fetch current usage and the last 30 days of snapshots. */
export const getStorage = () =>
  apiGet<StorageResponse>("/api/v1/admin/storage?days=30");

/** @brief Fetch one page of the per-user breakdown. */
export const getStorageUsers = (page = 1) =>
  apiGet<UserStoragePage>(
    `/api/v1/admin/storage/users?page=${page}&page_size=100`,
  );
