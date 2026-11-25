"use client";
/**
 * @file hooks/useCountdowns.ts
 * @brief Countdown queries and mutations (follow is optimistic).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import {
  createCountdown,
  deleteCountdown,
  followCountdown,
  getCountdown,
  listCountdowns,
  listFollowing,
  unfollowCountdown,
  updateCountdown,
  type Countdown,
  type CountdownInput,
} from "@/lib/api/countdowns";
import { qk } from "@/lib/query-keys";
import { useToasts } from "@/stores/toasts";

const KEY = ["countdowns"] as const;

/** @brief Countdowns visible to the viewer. */
export const useCountdowns = () =>
  useQuery({ queryKey: [...KEY, "list"], queryFn: listCountdowns });

/** @brief Countdowns the viewer follows (home strip). */
export const useFollowing = () =>
  useQuery({ queryKey: [...KEY, "following"], queryFn: listFollowing });

/** @brief One countdown. */
export const useCountdown = (id: string) =>
  useQuery({
    queryKey: [...KEY, id],
    queryFn: () => getCountdown(id),
    retry: false,
  });

/** @brief Apply a patch to a countdown in every cached list/detail. */
function patchAll(qc: QueryClient, id: string, f: (c: Countdown) => Countdown) {
  qc.setQueriesData<Countdown | Countdown[]>({ queryKey: KEY }, (d) =>
    Array.isArray(d)
      ? d.map((c) => (c.id === id ? f(c) : c))
      : d && d.id === id
        ? f(d)
        : d,
  );
}

/** @brief Refresh countdowns and the feed/Home posts that embed them. */
const refresh = (qc: QueryClient) => {
  void qc.invalidateQueries({ queryKey: KEY });
  void qc.invalidateQueries({ queryKey: qk.feed.all() });
  void qc.invalidateQueries({ queryKey: qk.home.feed() });
};

const fail = (message: string) => () =>
  useToasts.getState().push({ variant: "danger", message });

/** @brief Create a countdown. */
export function useCreateCountdown() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: CountdownInput) => createCountdown(b),
    onSuccess: () => refresh(qc),
    onError: fail("Could not create countdown."),
  });
}

/** @brief Update a countdown. */
export function useUpdateCountdown(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: Partial<CountdownInput>) => updateCountdown(id, b),
    onSuccess: () => refresh(qc),
    onError: fail("Could not save countdown."),
  });
}

/** @brief Delete a countdown. */
export function useDeleteCountdown() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCountdown(id),
    onSuccess: () => refresh(qc),
    onError: fail("Could not delete countdown."),
  });
}

/** @brief Follow/unfollow with optimistic follower count everywhere. */
export function useToggleFollow(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (follow: boolean) =>
      follow ? followCountdown(id) : unfollowCountdown(id),
    onMutate: async (follow) => {
      await qc.cancelQueries({ queryKey: KEY });
      const prev = qc.getQueriesData<Countdown | Countdown[]>({
        queryKey: KEY,
      });
      patchAll(qc, id, (c) => ({
        ...c,
        following: follow,
        follower_count: Math.max(0, c.follower_count + (follow ? 1 : -1)),
      }));
      return { prev };
    },
    onError: (_e, _f, ctx) => {
      ctx?.prev.forEach(([k, d]) => qc.setQueryData(k, d));
      fail("Could not update follow.")();
    },
    onSuccess: (c) => patchAll(qc, id, () => c),
    onSettled: () => void qc.invalidateQueries({ queryKey: KEY }),
  });
}
