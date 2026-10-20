"use client";
/**
 * @file hooks/useCalendarSubscriptions.ts
 * @brief TanStack Query hooks for calendar subscriptions CRUD + sync.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import {
  listSubscriptions,
  createSubscription,
  deleteSubscription,
  syncNowSubscription,
} from "@/lib/api/events";
import { useMutationWithToast } from "./useMutationWithToast";

/**
 * @brief Fetch all subscriptions for the current user.
 */
export function useCalendarSubscriptions() {
  return useQuery({
    queryKey: qk.events.subscriptions.list(),
    queryFn: listSubscriptions,
    staleTime: 60_000,
  });
}

/**
 * @brief Add a new calendar subscription.
 */
export function useAddSubscription() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: createSubscription,
    successKey: "toasts.calendar.subscription_added",
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.events.subscriptions.list() });
    },
  });
}

/**
 * @brief Delete a calendar subscription.
 */
export function useDeleteSubscription() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (id: string) => deleteSubscription(id),
    successKey: "toasts.calendar.subscription_deleted",
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.events.subscriptions.list() });
    },
  });
}

/**
 * @brief Sync a subscription immediately.
 */
export function useSyncNow() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (id: string) => syncNowSubscription(id),
    successKey: "toasts.calendar.sync_complete",
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.events.subscriptions.list() });
    },
  });
}
