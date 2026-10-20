"use client";
/**
 * @file app/app/media/page.tsx
 * @brief Media manager: upload zone + recent uploads grid.
 *
 * Backend has no media-list endpoint; uploaded items are tracked in
 * component-local state for the session. Persistence comes via galleries.
 */
import * as React from "react";
import { UploadZone } from "@/components/media/UploadZone";
import { MediaGrid } from "@/components/media/MediaGrid";
import type { MediaItem } from "@/lib/api/media";

export default function MediaPage() {
  const [recent, setRecent] = React.useState<MediaItem[]>([]);
  return (
    <div className="mx-auto max-w-[1200px] p-4 md:p-8">
      <h1 className="mb-6 text-3xl font-black tracking-tight">Media</h1>
      <div className="flex flex-col gap-6">
        <UploadZone onComplete={(m) => setRecent((cur) => [m, ...cur])} />
        <section>
          <h2 className="mb-3 text-lg font-semibold">Recent uploads</h2>
          <MediaGrid items={recent} />
        </section>
      </div>
    </div>
  );
}
