/**
 * @file components/subgroups/hub/CoverBand.tsx
 * @brief Cover band with media or deterministic gradient fallback + title overlay.
 */
"use client";

import * as React from "react";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { gradientFor } from "@/lib/groupVisuals";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface CoverBandProps {
  subgroup: SubgroupDetail;
  right?: React.ReactNode;
}

/**
 * @brief Group cover with title and meta overlaid on a legibility veil.
 * @param subgroup group detail
 * @param right optional node aligned bottom-right (e.g. chat toggle)
 * @return cover band
 */
export function CoverBand({ subgroup, right }: CoverBandProps) {
  const { background } = gradientFor(subgroup.slug);
  const hasCover = !!subgroup.cover_media_id;

  return (
    <div
      className="relative mb-6 h-60 w-full overflow-hidden sm:h-72 md:h-80"
      style={hasCover ? undefined : { background }}
    >
      {hasCover && (
        <MediaThumb mediaId={subgroup.cover_media_id} alt={subgroup.name} />
      )}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-3/5 bg-gradient-to-b from-transparent via-black/15 to-black/65"
      />
      <div className="absolute inset-x-4 bottom-4 flex items-end justify-between gap-4 sm:inset-x-5 md:inset-x-6 md:bottom-6">
        <div className="min-w-0 flex-1 text-white">
          <h1 className="mb-1 text-3xl font-black tracking-tight [text-shadow:0_2px_24px_rgba(0,0,0,0.6)] sm:text-4xl md:text-5xl">
            {subgroup.name}
          </h1>
          <p className="text-sm [text-shadow:0_1px_2px_rgba(0,0,0,0.5)]">
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
