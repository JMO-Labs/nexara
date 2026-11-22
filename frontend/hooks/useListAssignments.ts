"use client";
/**
 * @file hooks/useListAssignments.ts
 * @brief Take / assign / respond / release / unassign mutations for list
 *        items, plus the list activity (history) infinite query.
 */
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { listApi } from "@/lib/api/lists";
import { qk } from "@/lib/query-keys";
import { useSession } from "@/stores/session";

/** Actions the item row can fire; every one targets an item id. */
export interface ItemAssignActions {
  take: (itemId: string) => void;
  assign: (itemId: string, userId: string) => void;
  accept: (itemId: string) => void;
  decline: (itemId: string) => void;
  release: (itemId: string) => void;
  unassign: (itemId: string) => void;
  /** True while any assignment request is in flight. */
  busy: boolean;
}

/** @brief Viewer identity + whether they may assign/unassign (owner/admin). */
export interface ItemAssignContext {
  viewerId: string | undefined;
  canManage: boolean;
  actions: ItemAssignActions;
}

/**
 * @brief Assignment actions for one list; refreshes items and history after
 *        each change.
 * @param listId list id
 * @param ownerId list owner id (owners and site admins can assign)
 * @return viewer id, canManage flag and action callbacks
 */
export function useItemAssignments(
  listId: string,
  ownerId: string,
): ItemAssignContext {
  const qc = useQueryClient();
  const user = useSession((s) => s.user);
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: qk.lists.itemsAll(listId) });
    void qc.invalidateQueries({ queryKey: qk.lists.activity(listId) });
  };
  const opts = { onSuccess: refresh, silentSuccess: true };
  const take = useMutationWithToast({
    ...opts,
    mutationFn: (id: string) => listApi.takeItem(listId, id),
  });
  const assign = useMutationWithToast({
    ...opts,
    mutationFn: (v: { id: string; userId: string }) =>
      listApi.assignItem(listId, v.id, v.userId),
  });
  const respond = useMutationWithToast({
    ...opts,
    mutationFn: (v: { id: string; accept: boolean }) =>
      listApi.respondAssignment(listId, v.id, v.accept),
  });
  const release = useMutationWithToast({
    ...opts,
    mutationFn: (id: string) => listApi.releaseItem(listId, id),
  });
  const unassign = useMutationWithToast({
    ...opts,
    mutationFn: (id: string) => listApi.unassignItem(listId, id),
  });
  const viewerId = user?.id;
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  return {
    viewerId,
    canManage: Boolean(viewerId) && (viewerId === ownerId || isAdmin),
    actions: {
      take: (id) => take.mutate(id),
      assign: (id, userId) => assign.mutate({ id, userId }),
      accept: (id) => respond.mutate({ id, accept: true }),
      decline: (id) => respond.mutate({ id, accept: false }),
      release: (id) => release.mutate(id),
      unassign: (id) => unassign.mutate(id),
      busy: [take, assign, respond, release, unassign].some((m) => m.isPending),
    },
  };
}

/**
 * @brief Newest-first activity feed for a list.
 * @param listId list id; disabled when undefined
 * @param limit page size
 * @return infinite query result
 */
export function useListActivity(listId: string | undefined, limit = 30) {
  return useInfiniteQuery({
    queryKey: qk.lists.activity(listId ?? ""),
    queryFn: ({ pageParam }) =>
      listApi.getActivity(listId!, { cursor: pageParam, limit }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor,
    enabled: Boolean(listId),
    staleTime: 15_000,
  });
}
