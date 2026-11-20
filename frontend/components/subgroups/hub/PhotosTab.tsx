"use client";
/**
 * @file components/subgroups/hub/PhotosTab.tsx
 * @brief Photos tab: Albums | All photos switch over GalleriesTab and MediaTab.
 */
import * as React from "react";
import { Segmented } from "@/components/ui/page";
import type { SubgroupDetail } from "@/lib/api/subgroups";
import { GalleriesTab } from "./GalleriesTab";
import { MediaTab } from "./MediaTab";

type View = "albums" | "all";

const VIEWS: { value: View; label: string }[] = [
  { value: "albums", label: "Albums" },
  { value: "all", label: "All photos" },
];

export interface PhotosTabProps {
  subgroup: SubgroupDetail;
}

/**
 * @brief Group photos: albums or every photo in the group.
 * @param subgroup group detail
 * @return segmented switch and the selected view
 */
export function PhotosTab({ subgroup }: PhotosTabProps) {
  const [view, setView] = React.useState<View>("albums");
  return (
    <div className="flex flex-col gap-4">
      <div>
        <Segmented
          label="Photos view"
          options={VIEWS}
          value={view}
          onChange={setView}
        />
      </div>
      {view === "albums" ? (
        <GalleriesTab subgroup={subgroup} />
      ) : (
        <MediaTab subgroup={subgroup} />
      )}
    </div>
  );
}

export default PhotosTab;
