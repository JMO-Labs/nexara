"use client";
/**
 * @file components/events/RsvpInline.tsx
 * @brief Inline RSVP toggle row using rsvp_labels (defaults to attending/maybe/declined).
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import { useRsvp } from "@/hooks/useEvents";

const DEFAULT_LABELS: Record<string, string> = {
  attending: "Going",
  maybe: "Maybe",
  declined: "Decline",
};

export interface RsvpInlineProps {
  eventId: string;
  labels?: Record<string, string> | null;
  current?: string | null;
  counts?: Record<string, number>;
}

export function RsvpInline({
  eventId,
  labels,
  current,
  counts,
}: RsvpInlineProps) {
  const merged = labels && Object.keys(labels).length ? labels : DEFAULT_LABELS;
  const rsvp = useRsvp(eventId);
  const onClick = (status: string) => {
    rsvp.mutate(current === status ? null : status);
  };
  return (
    <div role="group" aria-label="RSVP" className="flex flex-wrap gap-2">
      {Object.entries(merged).map(([status, label]) => {
        const active = current === status;
        const count = counts?.[status] ?? 0;
        return (
          <button
            key={status}
            type="button"
            aria-pressed={active}
            onClick={() => onClick(status)}
            disabled={rsvp.isPending}
            className={cn(
              "inline-flex min-h-8 items-center rounded-full border px-3 text-sm font-semibold transition-colors outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50",
              active
                ? "border-accent bg-accent text-surface-strong"
                : "border-ink/30 bg-transparent text-ink hover:bg-bg",
            )}
          >
            {label}
            {count > 0 ? ` · ${count}` : ""}
          </button>
        );
      })}
    </div>
  );
}

export default RsvpInline;
