"use client";
/**
 * @file components/subgroups/SubgroupCard.tsx
 * @brief Group tile. Per-slug deterministic gradient gives each group a
 *        stable color identity unless a cover image exists. Click selects,
 *        secondary button joins/leaves.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Badge, Button } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import type { Subgroup } from "@/lib/api/subgroups";
import { gradientFor, monogram } from "@/lib/groupVisuals";
import { cn } from "@/lib/utils";

export interface SubgroupCardProps {
  subgroup: Subgroup;
  memberCount?: number;
  isMember?: boolean;
  onSelect: (slug: string) => void;
  onJoin?: (slug: string) => void;
  onLeave?: (slug: string) => void;
  busy?: boolean;
  /** Anchor tile = taller hero variant (used in the mosaic). */
  anchor?: boolean;
}

const LIGHT_BTN = "min-h-11 bg-white text-black/85 hover:bg-white/90";
const GLASS_BTN = "min-h-11 bg-white/15 text-white hover:bg-white/25";

/**
 * @brief Group tile card.
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
  anchor,
}: SubgroupCardProps) {
  const router = useRouter();
  const { background, monogramBg } = React.useMemo(
    () => gradientFor(subgroup.slug),
    [subgroup.slug],
  );
  const handleClick = () => onSelect(subgroup.slug);
  const stop = (fn?: (slug: string) => void) => (e: React.MouseEvent) => {
    e.stopPropagation();
    fn?.(subgroup.slug);
  };

  let cta: React.ReactNode;
  if (isMember) {
    cta = (
      <Button
        variant="ghost"
        size="sm"
        loading={busy}
        onClick={stop(onLeave)}
        className={GLASS_BTN}
      >
        Leave
      </Button>
    );
  } else if (subgroup.join_policy === "invite_only") {
    cta = (
      <Button
        size="sm"
        disabled
        className={cn(GLASS_BTN, "disabled:opacity-50")}
      >
        Invite required
      </Button>
    );
  } else {
    cta = (
      <Button
        variant="ghost"
        size="sm"
        loading={busy}
        onClick={stop(onJoin)}
        className={LIGHT_BTN}
      >
        {subgroup.join_policy === "admin_approval" ? "Request to join" : "Join"}
      </Button>
    );
  }

  return (
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
      style={{ background }}
      className={cn(
        "group/card relative h-full cursor-pointer overflow-hidden rounded-[1.25rem] text-white/90 shadow-lg outline-none transition-[transform,box-shadow] motion-safe:duration-500 motion-safe:hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        anchor
          ? "min-h-[320px] md:min-h-[420px]"
          : "min-h-[220px] md:min-h-[260px]",
      )}
    >
      {subgroup.cover_media_id && (
        <>
          <MediaThumb
            mediaId={subgroup.cover_media_id}
            alt={subgroup.name}
            zoomOnHover
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-black/5 to-black/65"
          />
        </>
      )}
      <div
        aria-hidden
        style={{ background: monogramBg }}
        className={cn(
          "absolute grid place-items-center rounded-full font-display text-black/80",
          anchor
            ? "top-6 left-6 size-16 text-[22px]"
            : "top-[18px] left-[18px] size-12 text-[17px]",
        )}
      >
        {monogram(subgroup.name)}
      </div>

      {subgroup.is_private && (
        <div
          className={cn(
            "absolute",
            anchor ? "top-7 right-6" : "top-5 right-[18px]",
          )}
        >
          <Badge className="bg-white/20 text-white uppercase tracking-widest">
            Private
          </Badge>
        </div>
      )}

      <div
        className={cn(
          "absolute inset-x-0 bottom-0 bg-gradient-to-b from-transparent via-black/45 to-black/70",
          anchor ? "p-6 md:p-8" : "p-4 md:p-5",
        )}
      >
        <p className="mb-1.5 text-xs uppercase tracking-widest text-white/70">
          {subgroup.join_policy.replace("_", " ")}
          {typeof memberCount === "number" && (
            <>
              <span className="mx-1.5 opacity-40">·</span>
              {memberCount} {memberCount === 1 ? "member" : "members"}
            </>
          )}
        </p>
        <h3
          className={cn(
            "font-semibold leading-tight tracking-tight text-white",
            anchor
              ? "text-[34px] md:text-[52px]"
              : "text-[22px] md:text-[28px]",
            subgroup.description && "mb-2",
          )}
        >
          {subgroup.name}
        </h3>
        {subgroup.description && (
          <p
            className={cn(
              "text-sm text-white/80",
              anchor ? "line-clamp-3 max-w-[78%]" : "line-clamp-2",
            )}
          >
            {subgroup.description}
          </p>
        )}
        <div className="mt-4 flex gap-2">
          {cta}
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/app/subgroups/${subgroup.slug}`);
            }}
            className="min-h-11 text-white/80 hover:bg-white/10 hover:text-white"
          >
            Open →
          </Button>
        </div>
      </div>
    </div>
  );
}

export default SubgroupCard;
