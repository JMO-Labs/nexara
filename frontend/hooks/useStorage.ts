"use client";
/**
 * @file hooks/useStorage.ts
 * @brief TanStack Query hook for a user's storage usage.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getStorage } from "@/lib/api/storage";

/**
 * @brief Fetch storage usage.
 * @param userId user id (query disabled when empty)
 * @return query result
 */
export function useStorage(userId: string) {
  return useQuery({
    queryKey: qk.storage.user(userId),
    queryFn: () => getStorage(userId),
    enabled: !!userId,
  });
}
