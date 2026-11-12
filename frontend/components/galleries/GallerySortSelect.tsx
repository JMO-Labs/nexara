"use client";
/**
 * @file components/galleries/GallerySortSelect.tsx
 * @brief Toggleable sort button row: Recent, Popular, Oldest.
 */
import * as React from "react";
import { Button } from "@/components/ui";

export type SortOption = "recent" | "popular" | "oldest";

export interface GallerySortSelectProps {
  sort: SortOption;
  onSortChange: (sort: SortOption) => void;
}

const SORTS: Array<{ value: SortOption; label: string }> = [
  { value: "recent", label: "Recent" },
  { value: "popular", label: "Popular" },
  { value: "oldest", label: "Oldest" },
];

/**
 * @brief Sort toggle row.
 * @param sort active sort
 * @param onSortChange called with the chosen sort
 * @return button group
 */
export function GallerySortSelect({
  sort,
  onSortChange,
}: GallerySortSelectProps) {
  return (
    <div role="group" aria-label="Sort galleries" className="flex gap-2">
      {SORTS.map(({ value, label }) => (
        <Button
          key={value}
          variant={sort === value ? "primary" : "ghost"}
          size="sm"
          className="min-h-11 sm:min-h-8"
          aria-pressed={sort === value}
          onClick={() => onSortChange(value)}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}

export default GallerySortSelect;
