"use client";
/**
 * @file components/admin/PromptsTab.tsx
 * @brief Admin prompts management tab with master-detail layout.
 *        List on the left (stacked on phone), edit form on the right.
 */
import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import {
  usePrompts,
  useCreatePrompt,
  useUpdatePrompt,
  useDeletePrompt,
  useSeedBuiltinPrompts,
} from "@/hooks/usePrompts";
import { Button, EmptyState } from "@/components/ui";
import type { PromptCreate, PromptUpdate } from "@/lib/api/prompts";
import { PromptList } from "./prompts-tab/PromptList";
import { PromptEditor } from "./prompts-tab/PromptEditor";
import { NewPromptModal } from "./prompts-tab/NewPromptModal";

/**
 * @brief Prompts admin tab.
 * @return tab content
 */
export function PromptsTab() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const { data: prompts = [], isLoading, error } = usePrompts();
  const updateMutation = useUpdatePrompt();
  const createMutation = useCreatePrompt();
  const deleteMutation = useDeletePrompt();
  const seedMutation = useSeedBuiltinPrompts();

  const selected = selectedId ? prompts.find((p) => p.id === selectedId) : null;

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2
          role="status"
          aria-label="Loading prompts"
          className="size-6 motion-safe:animate-spin"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-2xl border-l-4 border-danger bg-surface p-3"
      >
        Failed to load prompts
      </div>
    );
  }

  if (prompts.length === 0) {
    return (
      <EmptyState
        title="No prompts yet"
        action={
          <Button
            onClick={() => seedMutation.mutate()}
            loading={seedMutation.isPending}
          >
            <Plus className="size-4" aria-hidden="true" />
            Seed builtin library
          </Button>
        }
      />
    );
  }

  const handleUpdate = (update: PromptUpdate) => {
    if (selectedId)
      updateMutation.mutate({ promptId: selectedId, payload: update });
  };

  const handleCreate = (form: PromptCreate) => {
    createMutation.mutate(form);
    setIsCreating(false);
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
    if (selectedId === id) setSelectedId(null);
  };

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <PromptList
        prompts={prompts}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onToggle={(promptId, enabled) =>
          updateMutation.mutate({ promptId, payload: { enabled: !enabled } })
        }
        onNew={() => setIsCreating(true)}
      />
      {selected && (
        <PromptEditor
          prompt={selected}
          deleting={deleteMutation.isPending}
          onChange={handleUpdate}
          onDelete={() => handleDelete(selected.id)}
        />
      )}
      <NewPromptModal
        open={isCreating}
        creating={createMutation.isPending}
        onClose={() => setIsCreating(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
