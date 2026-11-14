"use client";
/**
 * @file hooks/useLists.ts
 * @brief TanStack Query hooks for lists, list items, signups and templates.
 *        List mutations invalidate ["lists", communityId]; item mutations
 *        invalidate ["listItems", listId].
 */
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { listApi } from "@/lib/api/lists";
import { templateApi } from "@/lib/api/listTemplates";
import type {
  ListCreateInput,
  ListItemCreateInput,
  ListTemplateCloneInput,
  ListUpdateInput,
  SignupClaimInput,
} from "@/lib/api/listTypes";

export function useLists(communityId: string | undefined, limit = 20) {
  return useQuery({
    queryKey: qk.lists.list(communityId ?? "", { limit }),
    queryFn: () => listApi.getLists({ limit }),
    enabled: Boolean(communityId),
    staleTime: 30_000,
  });
}

export function useListItems(listId: string | undefined, limit = 50) {
  return useInfiniteQuery({
    queryKey: qk.lists.items(listId ?? "", { limit }),
    queryFn: ({ pageParam }) =>
      listApi.listItems(listId!, { cursor: pageParam, limit }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor,
    enabled: Boolean(listId),
    staleTime: 15_000,
  });
}

export function useListCreate(communityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ListCreateInput) => listApi.createList(data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.all(communityId) }),
  });
}

export function useListUpdate(communityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; data: ListUpdateInput }) =>
      listApi.updateList(v.id, v.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.all(communityId) }),
  });
}

export function useListDelete(communityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => listApi.deleteList(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.all(communityId) }),
  });
}

export function useListItemCreate(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ListItemCreateInput) => listApi.createItem(listId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.itemsAll(listId) }),
  });
}

/** Toggle completion: `completed: true` completes, false un-completes. */
export function useListItemComplete(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { itemId: string; completed: boolean }) =>
      v.completed
        ? listApi.completeItem(listId, v.itemId)
        : listApi.uncompleteItem(listId, v.itemId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.itemsAll(listId) }),
  });
}

export function useListSignupClaim(listId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, ...data }: { itemId: string } & SignupClaimInput) =>
      listApi.claimSignup(listId, itemId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.itemsAll(listId) }),
  });
}

export function useListTemplates(limit = 50) {
  return useQuery({
    queryKey: [...qk.lists.templates(), { limit }] as const,
    queryFn: () => templateApi.getTemplates({ limit }),
    staleTime: 60_000,
  });
}

export function useListTemplateClone(communityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; options?: ListTemplateCloneInput }) =>
      templateApi.cloneTemplate(v.id, v.options),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.lists.all(communityId) }),
  });
}
