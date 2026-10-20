"use client";
/**
 * @file components/events/events-page/PeriodNav.tsx
 * @brief Prev / label / next row used above the week and day views.
 */
import { ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton } from "@/components/ui";

export interface PeriodNavProps {
  label: string;
  unit: "week" | "day";
  onPrev: () => void;
  onNext: () => void;
}

/**
 * @brief Period navigation row.
 * @param props label text, unit name for aria, handlers
 * @return nav element
 */
export function PeriodNav({ label, unit, onPrev, onNext }: PeriodNavProps) {
  return (
    <div className="flex items-center gap-2">
      <IconButton
        variant="outline"
        size="sm"
        aria-label={`Previous ${unit}`}
        onClick={onPrev}
      >
        <ChevronLeft className="size-4" />
      </IconButton>
      <div className="text-ink flex-1 text-center font-semibold">{label}</div>
      <IconButton
        variant="outline"
        size="sm"
        aria-label={`Next ${unit}`}
        onClick={onNext}
      >
        <ChevronRight className="size-4" />
      </IconButton>
    </div>
  );
}
