"use client";
/**
 * @file components/galleries/galleries-page/GalleryDrawer.tsx
 * @brief Drawer showing one gallery: owner, access settings, contributors,
 *        upload, items.
 */
import * as React from "react";
import Link from "next/link";
import { Play, Trash2 } from "lucide-react";
import {
  Avatar,
  Drawer,
  EmptyState,
  Button,
  IconButton,
  Skeleton,
} from "@/components/ui";
import { GalleryUpload } from "@/components/galleries/GalleryUpload";
import { EventGalleryBadge } from "@/components/galleries/EventGalleryBadge";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { GalleryCollaborators } from "./GalleryCollaborators";
import {
  useGalleryDetail,
  useGalleryItems,
  useUpdateGallery,
  useDeleteGallery,
  useRemoveItem,
} from "@/hooks/useGalleries";
import { useSetGalleryNsfw, useSetMediaNsfw } from "@/hooks/useNsfw";
import { NsfwCover } from "@/components/feed/NsfwCover";
import { NsfwToggle } from "@/components/compose/NsfwToggle";
import { useFeature } from "@/hooks/useFeature";
import { useIsGroupMod } from "@/hooks/useGroupMod";
import { useSession } from "@/stores/session";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { API_BASE } from "@/lib/auth/session";
import { useEventDetail } from "@/hooks/useEvents";
import { useMemberProfile } from "@/hooks/useMembers";
import { GalleryEventLink } from "./GalleryEventLink";
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

/** @brief Sentence-case a lowercase enum value, e.g. "owner only" -> "Owner only". */
function sentence(value: string): string {
  const text = value.replace("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * @brief Owner avatar, display name, item count and optional badge.
 * @param ownerId owner user id (resolved to a display name)
 * @param count number of items in the gallery
 * @param badge optional node shown under the count
 * @return owner header block
 */
function OwnerLine({
  ownerId,
  count,
  badge,
}: {
  ownerId: string;
  count: number;
  badge: React.ReactNode;
}) {
  const { data: owner } = useMemberProfile(ownerId);
  const name = owner?.display_name ?? "";
  return (
    <div className="flex min-w-0 flex-1 items-center gap-3">
      <Avatar src={`${API_BASE}/api/v1/users/${ownerId}/avatar`} name={name} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{name}</p>
        <p className="text-muted text-sm">
          {count} {count === 1 ? "item" : "items"}
        </p>
        {badge && <div className="mt-1">{badge}</div>}
      </div>
    </div>
  );
}

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
              "focus-visible:outline-accent min-h-9 rounded-full px-3 text-sm font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2",
              o === value ? "bg-surface-strong text-bg" : "glass-item text-ink",
              editable && o !== value && "hover:opacity-80",
            )}
          >
            {sentence(o)}
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
  const { data: linkedEvent } = useEventDetail(gallery?.event_id);
  const { data: items, isLoading } = useGalleryItems(galleryId);
  const sessionUser = useSession((s) => s.user);
  const confirm = useConfirmDialog((s) => s.confirm);
  const updateMut = useUpdateGallery();
  const deleteMut = useDeleteGallery();
  const removeItemMut = useRemoveItem(galleryId ?? "");
  const galleryNsfwMut = useSetGalleryNsfw();
  const mediaNsfwMut = useSetMediaNsfw();
  const groupMod = useIsGroupMod(gallery?.subgroup_id);
  const nsfwOn = useFeature("nsfw");
  const isAdult = sessionUser?.age_group === "adult";

  const isOwner =
    !!gallery && !!sessionUser && gallery.owner_id === sessionUser.id;
  const isMod =
    sessionUser?.role === "admin" || sessionUser?.role === "owner" || groupMod;
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
            <OwnerLine
              ownerId={gallery.owner_id}
              count={count}
              badge={gallery.event_id ? <EventGalleryBadge /> : null}
            />
            {isOwner && (
              <IconButton
                size="md"
                variant="glass"
                onClick={handleDelete}
                disabled={deleteMut.isPending}
                aria-label="Delete gallery"
              >
                <Trash2 className="size-5" aria-hidden="true" />
              </IconButton>
            )}
          </div>

          <GalleryEventLink
            eventId={gallery.event_id}
            title={linkedEvent?.title}
          />

          {gallery.description && (
            <p className="text-muted text-sm">{gallery.description}</p>
          )}

          {isOwner || isMod ? (
            isOwner ? (
              <NsfwToggle
                checked={!!gallery.is_nsfw}
                locked={gallery.nsfw_locked}
                onChange={(v) =>
                  updateMut.mutate({ id: gallery.id, body: { is_nsfw: v } })
                }
              />
            ) : (
              <Button
                variant="secondary"
                size="sm"
                className="self-start"
                onClick={() =>
                  galleryNsfwMut.mutate({
                    id: gallery.id,
                    value: !gallery.is_nsfw,
                  })
                }
              >
                {gallery.is_nsfw ? "Remove NSFW" : "Mark NSFW"}
              </Button>
            )
          ) : null}

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
            {count > 0 && (
              <Link
                href={`/app/galleries/${gallery.id}/slideshow`}
                className="focus-visible:outline-accent glass-item mb-3 inline-flex min-h-11 items-center gap-2 rounded-full px-4 text-sm font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
              >
                <Play className="size-4" aria-hidden="true" />
                Slideshow
              </Link>
            )}
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
                    className="group bg-bg relative aspect-square overflow-hidden rounded-[18px]"
                  >
                    <NsfwCover
                      nsfw={gallery.is_nsfw || it.is_nsfw}
                      itemId={`media:${it.media_id}`}
                      className="absolute inset-0"
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
                    </NsfwCover>
                    {isAdult && nsfwOn && it.added_by === sessionUser?.id && (
                      <IconButton
                        size="sm"
                        variant="glass"
                        aria-label={
                          it.is_nsfw
                            ? "Remove NSFW from photo"
                            : "Mark photo NSFW"
                        }
                        aria-pressed={!!it.is_nsfw}
                        onClick={() =>
                          mediaNsfwMut.mutate({
                            id: it.media_id,
                            value: !it.is_nsfw,
                          })
                        }
                        className="absolute top-1.5 left-1.5 text-xs font-bold"
                      >
                        NSFW
                      </IconButton>
                    )}
                    {isOwner && (
                      <IconButton
                        size="sm"
                        variant="glass"
                        onClick={() => handleRemoveItem(it.id)}
                        aria-label="Remove item"
                        className="hover-only absolute top-1.5 right-1.5 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
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
