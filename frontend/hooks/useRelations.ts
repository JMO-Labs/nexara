"use client";
/**
 * @file hooks/useRelations.ts
 * @brief Queries/mutations for relations; every write refreshes both lists.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  confirmRelation,
  listRelationRequests,
  listRelations,
  removeRelation,
  requestRelation,
} from "@/lib/api/relations";

const KEY = ["relations"] as const;

/** @brief Relations of a member as the viewer may see them. */
export const useRelations = (userId: string, enabled = true) =>
  useQuery({
    queryKey: [...KEY, "list", userId],
    queryFn: () => listRelations(userId),
    enabled,
  });

/** @brief Pending requests sent to me. */
export const useRelationRequests = (enabled = true) =>
  useQuery({
    queryKey: [...KEY, "requests"],
    queryFn: listRelationRequests,
    enabled,
  });

/** @brief Request, confirm and remove. */
export function useRelationActions() {
  const qc = useQueryClient();
  const done = () => void qc.invalidateQueries({ queryKey: KEY });
  return {
    request: useMutation({ mutationFn: requestRelation, onSuccess: done }),
    confirm: useMutation({ mutationFn: confirmRelation, onSuccess: done }),
    remove: useMutation({ mutationFn: removeRelation, onSuccess: done }),
  };
}
