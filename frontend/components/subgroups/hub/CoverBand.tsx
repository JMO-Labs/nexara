/**
 * @file components/subgroups/hub/CoverBand.tsx
 * @brief Compact cover band (<=220px, rounded 32): media or colour wash from
 *        groupColor, title on a glass overlay bottom-left, actions right.
 */
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { groupColor } from "@/lib/groupColor";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface CoverBandProps {
  subgroup: SubgroupDetail;
  right?: React.ReactNode;
}

/**
 * @brief Group cover with title and meta on a glass overlay.
 * @param subgroup group detail
 * @param right optional node aligned bottom-right (e.g. chat toggle)
 * @return cover band
 */
export function CoverBand({ subgroup, right }: CoverBandProps) {
  const accent = groupColor(subgroup.id, subgroup.accent_color);
  const hasCover = !!subgroup.cover_media_id;

  return (
    <div
      className={cn(
        "relative mb-4 w-full overflow-hidden rounded-[32px] md:mb-[18px]",
        hasCover ? "h-[180px] md:h-[220px]" : "h-[140px] md:h-[160px]",
      )}
      style={{
        background: `color-mix(in srgb, ${accent} 25%, transparent)`,
      }}
    >
      {hasCover && (
        <MediaThumb mediaId={subgroup.cover_media_id} alt={subgroup.name} />
      )}
      <div className="absolute inset-x-3 bottom-3 flex items-end justify-between gap-3 md:inset-x-4 md:bottom-4">
        <div className="glass min-w-0 rounded-[24px] px-4 py-2.5">
          <h1 className="truncate text-2xl font-medium tracking-tight text-ink md:text-3xl">
            {subgroup.name}
          </h1>
          <p className="text-sm text-muted">
            {subgroup.member_count} members ·{" "}
            {subgroup.is_private ? "private" : "public"}
          </p>
        </div>
        {right && <div className="shrink-0">{right}</div>}
      </div>
    </div>
  );
}

export default CoverBand;
