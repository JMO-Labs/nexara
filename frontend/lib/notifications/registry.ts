/**
 * @file lib/notifications/registry.ts
 * @brief Client mirror of the server notification type registry.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { listTypes } from "@/lib/api/notifications";
import type { NotificationTypeDescriptor } from "./types";

/** @brief Fetch (and cache forever) the notification type descriptors. */
export function useNotificationRegistry() {
  const q = useQuery({
    queryKey: ["notifications", "types"],
    queryFn: listTypes,
    staleTime: Infinity,
    gcTime: Infinity,
  });
  const types = useMemo(() => q.data ?? [], [q.data]);
  const byKey = useMemo(
    () =>
      new Map<string, NotificationTypeDescriptor>(types.map((d) => [d.key, d])),
    [types],
  );
  return { types, byKey, isLoading: q.isLoading, error: q.error };
}

/** @brief Descriptor for a type key, or null if unknown / not loaded. */
export function useNotificationType(
  key: string,
): NotificationTypeDescriptor | null {
  return useNotificationRegistry().byKey.get(key) ?? null;
}
