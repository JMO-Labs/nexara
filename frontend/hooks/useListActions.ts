"use client";
/**
 * @file hooks/useListActions.ts
 * @brief Secondary list hooks: archive, item update/delete and members.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { listApi } from "@/lib/api/lists";
import type { ListMemberAddInput } from "@/lib/api/listTypes";

/** @brief Archive a list; refreshes the community's lists. */
export function useListArchive(communityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => listApi.archiveList(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.all(communityId) }),
  });
}

/** @brief Replace an item's values. */
export function useListItemUpdate(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { itemId: string; values: Record<string, unknown> }) =>
      listApi.updateItem(listId, v.itemId, { values: v.values }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.itemsAll(listId) }),
  });
}

/** @brief Delete an item. */
export function useListItemDelete(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => listApi.deleteItem(listId, itemId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.itemsAll(listId) }),
  });
}

/** @brief Members of a list. */
export function useListMembers(listId: string | undefined) {
  return useQuery({
    queryKey: qk.lists.members(listId ?? ""),
    queryFn: () => listApi.getMembers(listId!),
    enabled: Boolean(listId),
  });
}

/** @brief Add a member by user id. */
export function useListMemberAdd(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ListMemberAddInput) => listApi.addMember(listId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.members(listId) }),
  });
}

/** @brief Remove a member by user id. */
export function useListMemberRemove(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => listApi.removeMember(listId, userId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.members(listId) }),
  });
}
