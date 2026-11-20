"use client";
/**
 * @file components/ui/page/Segmented.tsx
 * @brief Single-choice pill group (radiogroup) with an ink active pill.
 */
import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SegmentedProps<T extends string> {
  options: { value: T; label: string; icon?: LucideIcon }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}

/**
 * @brief Segmented control; arrow keys move and select (wraps).
 * @param label accessible group name
 * @return radiogroup
 */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: SegmentedProps<T>) {
  const refs = React.useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: React.KeyboardEvent, i: number) => {
    const n = options.length;
    let next = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (i + 1) % n;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp")
      next = (i - 1 + n) % n;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = n - 1;
    if (next < 0) return;
    e.preventDefault();
    onChange(options[next].value);
    refs.current[next]?.focus();
  };
  const hasValue = options.some((o) => o.value === value);
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="glass inline-flex max-w-full items-center gap-1 overflow-x-auto whitespace-nowrap rounded-full p-1"
    >
      {options.map((o, i) => {
        const active = o.value === value;
        const Icon = o.icon;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active || (!hasValue && i === 0) ? 0 : -1}
            onClick={() => onChange(o.value)}
            onKeyDown={(e) => onKey(e, i)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-full px-3.5 py-1.5 text-sm transition-colors outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
              active
                ? "bg-surface-strong text-bg"
                : "text-ink hover:bg-white/30",
            )}
          >
            {Icon && <Icon className="size-4" aria-hidden="true" />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
