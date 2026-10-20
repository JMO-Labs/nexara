"use client";
/**
 * @file components/galleries/GallerySortSelect.tsx
 * @brief Toggleable sort chip row: Recent · Popular · Oldest.
 */
import * as React from "react";
import Button from "@mui/joy/Button";
import Stack from "@mui/joy/Stack";

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

export function GallerySortSelect({
  sort,
  onSortChange,
}: GallerySortSelectProps) {
  return (
    <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
      {SORTS.map(({ value, label }) => (
        <Button
          key={value}
          variant={sort === value ? "soft" : "plain"}
          color={sort === value ? "primary" : "neutral"}
          onClick={() => onSortChange(value)}
          aria-pressed={sort === value}
          size="sm"
          sx={{ cursor: "pointer" }}
        >
          {label}
        </Button>
      ))}
    </Stack>
  );
}

export default GallerySortSelect;
