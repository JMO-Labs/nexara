"use client";
/**
 * @file components/galleries/galleries-page/GalleryDrawer.tsx
 * @brief Drawer showing one gallery: owner, access settings, contributors,
 *        upload, items.
 */
import * as React from "react";
import { Trash2 } from "lucide-react";
import {
  Avatar,
  Drawer,
  EmptyState,
  IconButton,
  Skeleton,
} from "@/components/ui";
import { GalleryUpload } from "@/components/galleries/GalleryUpload";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { GalleryCollaborators } from "./GalleryCollaborators";
import {
  useGalleryDetail,
  useGalleryItems,
  useUpdateGallery,
  useDeleteGallery,
  useRemoveItem,
} from "@/hooks/useGalleries";
import { useSession } from "@/stores/session";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { API_BASE } from "@/lib/auth/session";
import { cn } from "@/lib/utils";
import type { Gallery } from "@/lib/api/galleries";

const VISIBILITY: Array<Gallery["visibility"]> = [
  "private",
  "subgroup",
  "community",
];
const POLICY: Array<Gallery["contribution_policy"]> = [
  "owner_only",
  "collaborators",
  "community",
];

/** @brief Small section heading. */
function Label({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-2 text-sm font-semibold">{children}</h3>;
}

/**
 * @brief Row of option pills; editable by the owner only.
 * @param label group label
 * @param options available values
 * @param value current value
 * @param editable whether pills can be changed
 * @param onPick called with the chosen value
 * @return pill group
 */
function OptionPills<T extends string>({
  label,
  options,
  value,
  editable,
  onPick,
}: {
  label: string;
  options: T[];
  value: T;
  editable: boolean;
  onPick: (v: T) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div role="group" aria-label={label} className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            aria-pressed={o === value}
            disabled={!editable || o === value}
            onClick={() => onPick(o)}
            className={cn(
              "focus-visible:outline-accent min-h-11 rounded-full px-3 text-xs font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2 sm:min-h-8",
              o === value ? "bg-accent text-surface-strong" : "bg-bg text-ink",
              editable && o !== value && "hover:opacity-80",
            )}
          >
            {o.replace("_", " ")}
          </button>
        ))}
      </div>
    </div>
  );
}

export interface GalleryDrawerProps {
  galleryId: string | null;
  onClose: () => void;
  onOpenItem: (idx: number) => void;
  /** True while the Lightbox is open: only one Radix modal layer may be mounted. */
  suspended?: boolean;
}

/**
 * @brief Gallery detail drawer.
 * @param galleryId selected gallery id or null (closed)
 * @param onClose close handler
 * @param onOpenItem open the lightbox at an index
 * @return drawer element
 */
export function GalleryDrawer({
  galleryId,
  suspended = false,
  onClose,
  onOpenItem,
}: GalleryDrawerProps) {
  const { data: gallery } = useGalleryDetail(galleryId);
  const { data: items, isLoading } = useGalleryItems(galleryId);
  const sessionUser = useSession((s) => s.user);
  const confirm = useConfirmDialog((s) => s.confirm);
  const updateMut = useUpdateGallery();
  const deleteMut = useDeleteGallery();
  const removeItemMut = useRemoveItem(galleryId ?? "");

  const isOwner =
    !!gallery && !!sessionUser && gallery.owner_id === sessionUser.id;
  const canContribute =
    isOwner ||
    (!!gallery &&
      (gallery.contribution_policy === "community" ||
        gallery.contribution_policy === "collaborators"));
  const count = items?.length ?? 0;

  const handleDelete = async () => {
    if (!gallery) return;
    const ok = await confirm({
      title: `Delete gallery?`,
      message: `Delete "${gallery.title}"? This cannot be undone.`,
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (!ok) return;
    deleteMut.mutate(gallery.id, { onSuccess: () => onClose() });
  };

  const handleRemoveItem = async (itemId: string) => {
    const ok = await confirm({
      title: "Remove item?",
      message: "Remove this item from the gallery?",
      confirmLabel: "Remove",
      tone: "danger",
    });
    if (!ok) return;
    removeItemMut.mutate(itemId);
  };

  return (
    <Drawer
      open={!!galleryId && !suspended}
      onClose={onClose}
      title={gallery?.title ?? "Gallery"}
    >
      {!gallery ? (
        <Skeleton height={200} />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <Avatar
              src={`${API_BASE}/api/v1/users/${gallery.owner_id}/avatar`}
              name={gallery.owner_id}
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">
                {gallery.owner_id}
              </p>
              <p className="text-muted text-sm">
                {count} {count === 1 ? "item" : "items"}
              </p>
            </div>
            {isOwner && (
              <IconButton
                size="md"
                variant="ghost"
                onClick={handleDelete}
                disabled={deleteMut.isPending}
                aria-label="Delete gallery"
              >
                <Trash2 className="size-5" aria-hidden="true" />
              </IconButton>
            )}
          </div>

          {gallery.description && (
            <p className="text-muted text-sm">{gallery.description}</p>
          )}

          <div className="flex flex-col gap-4">
            <OptionPills
              label="Visibility"
              options={VISIBILITY}
              value={gallery.visibility}
              editable={isOwner}
              onPick={(v) =>
                updateMut.mutate({ id: gallery.id, body: { visibility: v } })
              }
            />
            <OptionPills
              label="Who can contribute"
              options={POLICY}
              value={gallery.contribution_policy}
              editable={isOwner}
              onPick={(p) =>
                updateMut.mutate({
                  id: gallery.id,
                  body: { contribution_policy: p },
                })
              }
            />
          </div>

          {gallery.contribution_policy === "collaborators" && (
            <GalleryCollaborators
              galleryId={gallery.id}
              ownerId={gallery.owner_id}
              isOwner={isOwner}
            />
          )}

          {canContribute && (
            <div>
              <Label>Add content</Label>
              <GalleryUpload galleryId={gallery.id} />
            </div>
          )}

          <div>
            <Label>Items</Label>
            {isLoading && <Skeleton height={200} />}
            {!isLoading && count === 0 && (
              <EmptyState
                compact
                title="No items yet"
                description="Add media to this gallery."
              />
            )}
            {count > 0 && (
              <ul className="grid grid-cols-3 gap-2">
                {items!.map((it, idx) => (
                  <li
                    key={it.id}
                    className="bg-bg relative aspect-square overflow-hidden rounded-xl"
                  >
                    <button
                      type="button"
                      onClick={() => onOpenItem(idx)}
                      aria-label={it.caption ?? `Item ${idx + 1}`}
                      className="focus-visible:outline-accent absolute inset-0 focus-visible:outline-2 focus-visible:-outline-offset-2"
                    >
                      <MediaThumb
                        mediaId={it.media_id}
                        alt={it.caption ?? `Item ${idx + 1}`}
                      />
                    </button>
                    {isOwner && (
                      <IconButton
                        size="sm"
                        variant="destructive"
                        onClick={() => handleRemoveItem(it.id)}
                        aria-label="Remove item"
                        className="absolute top-1 right-1"
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </IconButton>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
