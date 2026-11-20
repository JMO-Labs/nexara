"use client";
/**
 * @file components/subgroups/SubgroupCard.tsx
 * @brief Glass group card: 16:9 cover image or colour wash from groupColor,
 *        name, 2-line description, optional avatar stack and Join / Open actions.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Lock } from "lucide-react";
import { Button } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import type { Subgroup } from "@/lib/api/subgroups";
import { groupColor } from "@/lib/groupColor";
import { monogram } from "@/lib/groupVisuals";

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
            background: `linear-gradient(135deg, color-mix(in srgb, ${color} 55%, transparent), color-mix(in srgb, ${color} 18%, transparent))`,
          }}
        >
          {subgroup.cover_media_id ? (
            <MediaThumb mediaId={subgroup.cover_media_id} alt="" zoomOnHover />
          ) : (
            <span
              aria-hidden
              className="absolute inset-0 grid place-items-center text-4xl font-bold text-ink/60"
            >
              {monogram(subgroup.name)}
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
          <p className="text-xs text-muted">
            {subgroup.join_policy.replace("_", " ")}
            {typeof memberCount === "number" && (
              <>
                {" · "}
                {memberCount} {memberCount === 1 ? "member" : "members"}
              </>
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
              variant="ghost"
              loading={busy}
              onClick={() => onLeave?.(subgroup.slug)}
            >
              Leave
            </Button>
          )}
          {cta}
          <Button
            size="sm"
            variant="glass"
            onClick={() => router.push(`/app/subgroups/${subgroup.slug}`)}
          >
            Open →
          </Button>
        </div>
      </div>
    </article>
  );
}

export default SubgroupCard;
