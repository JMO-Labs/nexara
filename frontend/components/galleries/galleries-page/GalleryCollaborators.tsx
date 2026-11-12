"use client";
/**
 * @file components/galleries/galleries-page/GalleryCollaborators.tsx
 * @brief Gallery contributors list; owner can add/remove community members.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { Button, IconButton } from "@/components/ui";
import {
  useCollaborators,
  useAddCollaborator,
  useRemoveCollaborator,
} from "@/hooks/useGalleries";
import { listUsers } from "@/lib/api/users";

export interface GalleryCollaboratorsProps {
  galleryId: string;
  ownerId: string;
  isOwner: boolean;
}

/**
 * @brief Contributors section for a gallery with the "collaborators" policy.
 * @param galleryId gallery id
 * @param ownerId gallery owner (never offered as a collaborator)
 * @param isOwner whether the viewer may edit the list
 * @return section element
 */
export function GalleryCollaborators({
  galleryId,
  ownerId,
  isOwner,
}: GalleryCollaboratorsProps) {
  const { data: collaborators = [] } = useCollaborators(galleryId);
  const { data: users } = useQuery({
    queryKey: ["users", "list", "all"],
    queryFn: () => listUsers(null, 100),
    staleTime: 60_000,
  });
  const addMut = useAddCollaborator(galleryId);
  const removeMut = useRemoveCollaborator(galleryId);
  const [pick, setPick] = React.useState("");
  const selectId = React.useId();

  const members = users?.items ?? [];
  const nameOf = (id: string) =>
    members.find((u) => u.id === id)?.display_name ?? id;
  const taken = new Set([ownerId, ...collaborators.map((c) => c.user_id)]);
  const candidates = members.filter((u) => !taken.has(u.id));

  const handleAdd = () => {
    if (!pick) return;
    addMut.mutate(pick, { onSuccess: () => setPick("") });
  };

  return (
    <section aria-labelledby={`${selectId}-h`}>
      <h3 id={`${selectId}-h`} className="mb-2 text-sm font-semibold">
        Contributors
      </h3>
      {collaborators.length === 0 ? (
        <p className="text-muted text-sm">No contributors yet.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {collaborators.map((c) => {
            const name = nameOf(c.user_id);
            return (
              <li
                key={c.user_id}
                className="bg-bg flex min-h-11 items-center justify-between gap-2 rounded-xl px-3"
              >
                <span className="truncate text-sm">{name}</span>
                {isOwner && (
                  <IconButton
                    size="sm"
                    variant="ghost"
                    aria-label={`Remove ${name}`}
                    disabled={removeMut.isPending}
                    onClick={() => removeMut.mutate(c.user_id)}
                  >
                    <X className="size-4" aria-hidden="true" />
                  </IconButton>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {isOwner && (
        <div className="mt-3 flex gap-2">
          <label htmlFor={selectId} className="sr-only">
            Add contributor
          </label>
          <select
            id={selectId}
            value={pick}
            onChange={(e) => setPick(e.target.value)}
            className="bg-bg text-ink focus-visible:outline-accent min-h-11 min-w-0 flex-1 rounded-xl px-3 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
          >
            <option value="">Choose a member…</option>
            {candidates.map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name}
              </option>
            ))}
          </select>
          <Button
            type="button"
            size="md"
            onClick={handleAdd}
            disabled={!pick || addMut.isPending}
          >
            Add
          </Button>
        </div>
      )}
    </section>
  );
}
