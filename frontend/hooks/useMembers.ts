"use client";
/**
 * @file hooks/useMembers.ts
 * @brief People directory (infinite) and member profile queries.
 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import {
  getDirectory,
  getUserProfile,
  type DirectoryFilter,
} from "@/lib/api/users";

/**
 * @brief Infinite directory query.
 * @param q search text
 * @param filter all | online | groups
 */
export function useDirectory(q: string, filter: DirectoryFilter) {
  return useInfiniteQuery({
    queryKey: qk.people.directory(q, filter),
    queryFn: ({ pageParam }) => getDirectory({ q, filter, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    staleTime: 30_000,
  });
}

/**
 * @brief Public profile of a member.
 * @param id user id
 */
export function useMemberProfile(id: string) {
  return useQuery({
    queryKey: qk.people.profile(id),
    queryFn: () => getUserProfile(id),
  });
}

/**
 * @brief Directory entry (shared groups, presence) for one member, found by username.
 * @param id user id
 * @param username username used as the search term; disabled while undefined
 */
export function useMemberConnection(id: string, username?: string) {
  return useQuery({
    queryKey: qk.people.directory(`@${username ?? ""}`, "all"),
    queryFn: async () => {
      const page = await getDirectory({ q: username, limit: 100 });
      return page.items.find((p) => p.user_id === id) ?? null;
    },
    enabled: !!username,
    staleTime: 30_000,
  });
}
