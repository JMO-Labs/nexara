"use client";
/**
 * @file hooks/useGalleries.ts
 * @brief Gallery CRUD + items hooks.
 */
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import {
  listGalleries,
  getGallery,
  createGallery,
  updateGallery,
  deleteGallery,
  listItems,
  removeItem,
  type CreateGalleryBody,
  type ListGalleriesParams,
} from "@/lib/api/galleries";

export function useGalleryList(params?: ListGalleriesParams | null) {
  return useQuery({
    queryKey: qk.galleries.list(
      (params as Record<string, unknown> | undefined) ?? {},
    ),
    queryFn: () => listGalleries(params ?? undefined),
    staleTime: 30_000,
  });
}

/**
 * @brief Cursor-paginated gallery list (next_cursor / has_more).
 * @param params list filters (cursor is managed by the query)
 * @return TanStack infinite query result
 */
export function useGalleryListInfinite(
  params?: Omit<ListGalleriesParams, "cursor"> | null,
) {
  return useInfiniteQuery({
    queryKey: [
      ...qk.galleries.list((params as Record<string, unknown>) ?? {}),
      "infinite",
    ] as const,
    queryFn: ({ pageParam }) =>
      listGalleries({ ...(params ?? {}), cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) =>
      last.has_more && last.next_cursor ? last.next_cursor : undefined,
    staleTime: 30_000,
  });
}

export function useGalleryDetail(id: string | null | undefined) {
  return useQuery({
    queryKey: qk.galleries.detail(id ?? ""),
    queryFn: () => getGallery(id as string),
    enabled: !!id,
  });
}

export function useGalleryItems(id: string | null | undefined) {
  return useQuery({
    queryKey: [...qk.galleries.detail(id ?? ""), "items"] as const,
    queryFn: () => listItems(id as string),
    enabled: !!id,
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>, id?: string) {
  qc.invalidateQueries({ queryKey: qk.galleries.all() });
  if (id) qc.invalidateQueries({ queryKey: qk.galleries.detail(id) });
}

export function useCreateGallery() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (body: CreateGalleryBody) => createGallery(body),
    successKey: "toasts.galleries.created",
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateGallery() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: Partial<CreateGalleryBody>;
    }) => updateGallery(id, body),
    successKey: "toasts.galleries.updated",
    onSuccess: (_data, vars) => invalidateAll(qc, vars.id),
  });
}

export function useDeleteGallery() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (id: string) => deleteGallery(id),
    successKey: "toasts.galleries.deleted",
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRemoveItem(galleryId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (itemId: string) => removeItem(galleryId, itemId),
    onSuccess: () => invalidateAll(qc, galleryId),
  });
}
