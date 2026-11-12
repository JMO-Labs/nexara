"use client";
/**
 * @file components/galleries/galleries-page/GalleryCollaborators.tsx
 * @brief Collaborator list with owner-only add/remove controls.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import {
  useCollaborators,
  useAddCollaborator,
  useRemoveCollaborator,
} from "@/hooks/useGalleries";
import { listUsers } from "@/lib/api/users";

export interface GalleryCollaboratorsProps {
  galleryId: string;
  isOwner: boolean;
}

/**
 * @brief Contributors section for a gallery drawer.
 * @param galleryId gallery id
 * @param isOwner whether add/remove controls are shown
 * @return section element
 */
export function GalleryCollaborators({
  galleryId,
  isOwner,
}: GalleryCollaboratorsProps) {
  const [pick, setPick] = React.useState("");
  const { data: collabs } = useCollaborators(galleryId);
  const addMut = useAddCollaborator(galleryId);
  const removeMut = useRemoveCollaborator(galleryId);
  const { data: users } = useQuery({
    queryKey: ["users", "list", "all"],
    queryFn: () => listUsers(null, 100),
    staleTime: 60_000,
  });

  const members = users?.items ?? [];
  const name = (id: string) =>
    members.find((u) => u.id === id)?.display_name ?? id;
  const taken = new Set((collabs ?? []).map((c) => c.user_id));
  const options = members.filter((u) => !taken.has(u.id));

  return (
    <section aria-label="Contributors">
      <h3 className="mb-2 text-sm font-semibold">Contributors</h3>
      {(collabs ?? []).length === 0 ? (
        <p className="text-muted text-sm">No contributors yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {collabs!.map((c) => (
            <li key={c.user_id} className="flex items-center gap-2 text-sm">
              <span className="min-w-0 flex-1 truncate">{name(c.user_id)}</span>
              {isOwner && (
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Remove ${name(c.user_id)}`}
                  disabled={removeMut.isPending}
                  onClick={() => removeMut.mutate(c.user_id)}
                >
                  Remove
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {isOwner && (
        <div className="mt-3 flex items-center gap-2">
          <select
            aria-label="Member"
            value={pick}
            onChange={(e) => setPick(e.target.value)}
            className="bg-bg focus-visible:outline-accent min-h-10 min-w-0 flex-1 rounded-xl px-3 text-sm outline-none focus-visible:outline-2"
          >
            <option value="">Select member…</option>
            {options.map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name}
              </option>
            ))}
          </select>
          <Button
            size="md"
            disabled={!pick || addMut.isPending}
            onClick={() => {
              addMut.mutate(pick);
              setPick("");
            }}
          >
            Add
          </Button>
        </div>
      )}
    </section>
  );
}
