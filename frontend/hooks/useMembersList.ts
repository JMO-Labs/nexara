"use client";
/**
 * @file hooks/useMembersList.ts
 * @brief All community members (name/avatar) for pickers; cached 5 minutes.
 */
import { useQuery } from "@tanstack/react-query";
import { listUsers, type UserSummary } from "@/lib/api/users";

// ponytail: one page of 100 covers a family community; page it if that grows.
export function useMembersList() {
  return useQuery({
    queryKey: ["members", "all"],
    queryFn: async () => (await listUsers(null, 100)).items,
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
export function matchMembers(
  list: UserSummary[],
  q: string,
  limit = 6,
): UserSummary[] {
  const n = q.toLowerCase();
  const rank = (u: UserSummary) =>
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
