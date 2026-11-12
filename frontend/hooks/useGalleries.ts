"use client";
/**
 * @file hooks/useGalleries.ts
 * @brief Gallery CRUD + items + collaborators hooks.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  listCollaborators,
  addCollaborator,
  removeCollaborator,
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

const collabKey = (id: string) =>
  [...qk.galleries.detail(id), "collaborators"] as const;

export function useCollaborators(id: string | null | undefined) {
  return useQuery({
    queryKey: collabKey(id ?? ""),
    queryFn: () => listCollaborators(id as string),
    enabled: !!id,
  });
}

export function useAddCollaborator(galleryId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (userId: string) => addCollaborator(galleryId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: collabKey(galleryId) }),
  });
}

export function useRemoveCollaborator(galleryId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (userId: string) => removeCollaborator(galleryId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: collabKey(galleryId) }),
  });
}
