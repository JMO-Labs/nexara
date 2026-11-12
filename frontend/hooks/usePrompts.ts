/**
 * @file hooks/usePrompts.ts
 * @brief Query and mutation hooks for prompts (admin + feed).
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import {
  listPrompts,
  createPrompt,
  updatePrompt,
  deletePrompt,
  getPromptPost,
  type PromptCreate,
  type PromptUpdate,
} from "@/lib/api/prompts";

/**
 * @brief Query hook to list all prompts (admin).
 */
export function usePrompts() {
  return useQuery({
    queryKey: qk.admin.prompts(),
    queryFn: listPrompts,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * @brief Mutation hook to create a new prompt (admin).
 */
export function useCreatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCreate) => createPrompt(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.prompts() });
    },
  });
}

/**
 * @brief Mutation hook to update a prompt (admin).
 */
export function useUpdatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      promptId,
      payload,
    }: {
      promptId: string;
      payload: PromptUpdate;
    }) => updatePrompt(promptId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.prompts() });
    },
  });
}

/**
 * @brief Mutation hook to delete a prompt (admin).
 */
export function useDeletePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (promptId: string) => deletePrompt(promptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.prompts() });
    },
  });
}

/**
 * @brief Query hook to fetch a prompt post by ID (feed view).
 * @param promptPostId Prompt post ID
 * @return Query result with PromptPost data
 */
export function usePromptPost(promptPostId?: string) {
  return useQuery({
    queryKey: qk.feed.promptPost(promptPostId ?? ""),
    queryFn: () =>
      promptPostId ? getPromptPost(promptPostId) : Promise.reject("No ID"),
    enabled: !!promptPostId,
    staleTime: 60_000,
  });
}
