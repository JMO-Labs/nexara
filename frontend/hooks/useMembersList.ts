"use client";
/**
 * @file hooks/useMembersList.ts
 * @brief All community members (name/avatar) for pickers; cached 5 minutes.
 */
import { useQuery } from "@tanstack/react-query";
import { listUsers, type UserSummary } from "@/lib/api/users";

// ponytail: one page of 100 covers a family community; page it if that grows.
/**
 * @param opts.bots include bot users (only @mention autocomplete/links want them)
 */
export function useMembersList({ bots = false }: { bots?: boolean } = {}) {
  return useQuery({
    queryKey: ["members", "all"],
    queryFn: async () => (await listUsers(null, 100)).items,
    select: (items) => (bots ? items : items.filter((u) => !u.is_bot)),
    staleTime: 5 * 60_000,
  });
}

/**
 * @brief Members whose name or username starts a word with ``q``.
 * @param list members
 * @param q query (no @)
 * @param limit max results
 * @return matches
 */
export function matchMembers<T extends UserSummary>(
  list: T[],
  q: string,
  limit = 6,
): T[] {
  const n = q.toLowerCase();
  const rank = (u: T) =>
    u.username.toLowerCase().startsWith(n)
      ? 0
      : u.display_name.toLowerCase().startsWith(n)
        ? 1
        : 2;
  return list
    .filter(
      (u) =>
        !n ||
        u.username.toLowerCase().startsWith(n) ||
        u.display_name
          .toLowerCase()
          .split(/\s+/)
          .some((w) => w.startsWith(n)),
    )
    .sort((a, b) => rank(a) - rank(b))
    .slice(0, limit);
}
