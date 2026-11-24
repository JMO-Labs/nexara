"use client";
/**
 * @file hooks/useCountdowns.ts
 * @brief Countdown queries and mutations (follow is optimistic).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCountdown,
  deleteCountdown,
  followCountdown,
  getCountdown,
  listCountdowns,
  unfollowCountdown,
  updateCountdown,
  type Countdown,
  type CountdownInput,
} from "@/lib/api/countdowns";

const KEY = ["countdowns"] as const;

/** @brief Countdowns visible to the viewer. */
export const useCountdowns = () =>
  useQuery({ queryKey: [...KEY, "list"], queryFn: listCountdowns });

/** @brief One countdown. */
export const useCountdown = (id: string) =>
  useQuery({
    queryKey: [...KEY, id],
    queryFn: () => getCountdown(id),
    retry: false,
  });

/** @brief Create a countdown. */
export function useCreateCountdown() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: CountdownInput) => createCountdown(b),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
      void qc.invalidateQueries({ queryKey: ["posts"] });
    },
  });
}

/** @brief Update a countdown. */
export function useUpdateCountdown(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: Partial<CountdownInput>) => updateCountdown(id, b),
    onSuccess: (c) => qc.setQueryData([...KEY, id], c),
  });
}

/** @brief Delete a countdown. */
export function useDeleteCountdown() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCountdown(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
      void qc.invalidateQueries({ queryKey: ["posts"] });
    },
  });
}

/** @brief Follow/unfollow with optimistic follower count. */
export function useToggleFollow(id: string) {
  const qc = useQueryClient();
  const key = [...KEY, id];
  return useMutation({
    mutationFn: (follow: boolean) =>
      follow ? followCountdown(id) : unfollowCountdown(id),
    onMutate: async (follow) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<Countdown>(key);
      if (prev)
        qc.setQueryData<Countdown>(key, {
          ...prev,
          following: follow,
          follower_count: Math.max(0, prev.follower_count + (follow ? 1 : -1)),
        });
      return { prev };
    },
    onError: (_e, _f, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
    },
    onSuccess: (c) => qc.setQueryData(key, c),
  });
}
