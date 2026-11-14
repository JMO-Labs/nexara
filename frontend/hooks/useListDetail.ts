"use client";
/**
 * @file hooks/useListDetail.ts
 * @brief Single-list and single-template queries plus template
 *        create/update mutations (invalidate ["listTemplates"]).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { listApi } from "@/lib/api/lists";
import { templateApi } from "@/lib/api/listTemplates";
import type { ListTemplateInput } from "@/lib/api/listTypes";

/**
 * @brief Fetch one list.
 * @param communityId tenant scope (query key only)
 * @param id list id; query disabled when undefined
 * @return query result
 */
export function useList(communityId: string, id: string | undefined) {
  return useQuery({
    queryKey: qk.lists.detail(communityId, id ?? ""),
    queryFn: () => listApi.getList(id!),
    enabled: Boolean(id),
    staleTime: 15_000,
  });
}

/**
 * @brief Fetch one list template.
 * @param id template id; query disabled when undefined
 * @return query result
 */
export function useListTemplate(id: string | undefined) {
  return useQuery({
    queryKey: [...qk.lists.templates(), "detail", id ?? ""] as const,
    queryFn: () => templateApi.getTemplate(id!),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

/** @brief Create a template; invalidates all template queries. */
export function useListTemplateCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ListTemplateInput) => templateApi.createTemplate(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.lists.templates() }),
  });
}

/** @brief Update a template; invalidates all template queries. */
export function useListTemplateUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; data: Partial<ListTemplateInput> }) =>
      templateApi.updateTemplate(v.id, v.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.lists.templates() }),
  });
}
