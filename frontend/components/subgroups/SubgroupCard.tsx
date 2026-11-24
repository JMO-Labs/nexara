"use client";
/**
 * @file components/subgroups/SubgroupCard.tsx
 * @brief Glass group card: 16:9 cover image or colour wash from groupColor,
 *        name, 2-line description, optional avatar stack and Join / Open actions.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Globe, Lock, Users } from "lucide-react";
import { Button } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import type { Subgroup } from "@/lib/api/subgroups";
import { groupColor } from "@/lib/groupColor";

export interface SubgroupCardProps {
  subgroup: Subgroup;
  memberCount?: number;
  isMember?: boolean;
  onSelect: (slug: string) => void;
  onJoin?: (slug: string) => void;
  onLeave?: (slug: string) => void;
  busy?: boolean;
  /** Optional member avatar stack rendered above the actions. */
  avatars?: React.ReactNode;
}

/** @brief Sentence-case policy labels shown on the card. */
const POLICY_LABEL: Record<Subgroup["join_policy"], string> = {
  open: "Open",
  admin_approval: "Approval required",
  invite_only: "Invite only",
};

/**
 * @brief Group card.
 * @param props subgroup data, membership state and callbacks
 * @return card element
 */
export function SubgroupCard({
  subgroup,
  memberCount,
  isMember,
  onSelect,
  onJoin,
  onLeave,
  busy,
  avatars,
}: SubgroupCardProps) {
  const router = useRouter();
  const color = groupColor(subgroup.id, subgroup.accent_color);
  const handleClick = () => onSelect(subgroup.slug);

  let cta: React.ReactNode = null;
  if (!isMember) {
    cta =
      subgroup.join_policy === "invite_only" ? (
        <Button size="sm" variant="glass" disabled>
          Invite required
        </Button>
      ) : (
        <Button
          size="sm"
          loading={busy}
          onClick={() => onJoin?.(subgroup.slug)}
        >
          {subgroup.join_policy === "admin_approval"
            ? "Request to join"
            : "Join"}
        </Button>
      );
  }

  return (
    <article className="glass flex h-full flex-col overflow-hidden rounded-[32px]">
      <div
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.target !== e.currentTarget) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleClick();
          }
        }}
        className="flex flex-1 cursor-pointer flex-col outline-none focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
      >
        <div
          className="relative aspect-video w-full overflow-hidden"
          style={{
            background: `color-mix(in srgb, ${color} 25%, transparent)`,
          }}
        >
          {subgroup.cover_media_id ? (
            <MediaThumb
              mediaId={subgroup.cover_media_id}
              alt=""
              zoomOnHover
              nsfw={subgroup.cover_is_nsfw}
            />
          ) : (
            <span
              aria-hidden
              className="absolute inset-0 grid place-items-center"
            >
              <span className="glass-item grid size-14 place-items-center rounded-full text-ink">
                <Users className="size-6" />
              </span>
            </span>
          )}
          {subgroup.is_private && (
            <span className="glass-item absolute top-3 right-3 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs text-ink">
              <Lock className="size-3" aria-hidden="true" />
              Private
            </span>
          )}
        </div>
        <div className="flex flex-1 flex-col gap-1 p-4">
          <h3 className="truncate text-lg font-semibold tracking-tight text-ink">
            {subgroup.name}
          </h3>
          <p className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <span className="glass-item inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-ink">
              {subgroup.join_policy === "open" && (
                <Globe className="size-3" aria-hidden="true" />
              )}
              {POLICY_LABEL[subgroup.join_policy]}
            </span>
            {typeof memberCount === "number" && (
              <span>
                {memberCount} {memberCount === 1 ? "member" : "members"}
              </span>
            )}
          </p>
          {subgroup.description && (
            <p className="line-clamp-2 text-sm text-muted">
              {subgroup.description}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between gap-2 px-4 pb-4">
        <div className="min-w-0">{avatars}</div>
        <div className="flex shrink-0 items-center gap-2">
          {isMember && (
            <Button
              size="sm"
              variant="glass"
              loading={busy}
              onClick={() => onLeave?.(subgroup.slug)}
            >
              Leave
            </Button>
          )}
          {cta}
          <Button
            size="sm"
            aria-label={`Open ${subgroup.name}`}
            onClick={() => router.push(`/app/subgroups/${subgroup.slug}`)}
          >
            Open
          </Button>
        </div>
      </div>
    </article>
  );
}

export default SubgroupCard;
