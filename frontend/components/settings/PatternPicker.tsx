"use client";
/**
 * @file components/settings/PatternPicker.tsx
 * @brief Accessible radiogroup of home background patterns with live swatches.
 */
import { PATTERNS, patternUrl, type HomePattern } from "@/lib/patterns";
import { cn } from "@/lib/utils";

const LABELS: Record<HomePattern, string> = {
  none: "None",
  dots: "Dots",
  topo: "Topographic",
  contour: "Contour",
  waves: "Waves",
  grain: "Grain",
};

interface PatternPickerProps {
  label: string;
  value: HomePattern | null;
  onChange: (v: HomePattern | null) => void;
  /** @brief Adds a "Community default" (null) option. */
  allowDefault?: boolean;
  disabled?: boolean;
}

/**
 * @brief Radiogroup of pattern swatches.
 * @param props label, value, onChange, optional allowDefault/disabled
 * @return picker element
 */
export function PatternPicker({
  label,
  value,
  onChange,
  allowDefault = false,
  disabled,
}: PatternPickerProps) {
  const options: { v: HomePattern | null; text: string }[] = [
    ...(allowDefault ? [{ v: null, text: "Community default" }] : []),
    ...PATTERNS.map((p) => ({ v: p as HomePattern | null, text: LABELS[p] })),
  ];
  const onKey = (e: React.KeyboardEvent<HTMLButtonElement>, i: number) => {
    const d =
      e.key === "ArrowRight" || e.key === "ArrowDown"
        ? 1
        : e.key === "ArrowLeft" || e.key === "ArrowUp"
          ? -1
          : 0;
    if (!d) return;
    e.preventDefault();
    const next = (i + d + options.length) % options.length;
    onChange(options[next].v);
    const btns = e.currentTarget.parentElement?.querySelectorAll("button");
    btns?.[next]?.focus();
  };
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="grid grid-cols-2 gap-2 md:grid-cols-3"
    >
      {options.map(({ v, text }, i) => {
        const checked = v === value;
        const url = v ? patternUrl(v) : null;
        return (
          <button
            key={text}
            type="button"
            role="radio"
            aria-checked={checked}
            aria-label={text}
            disabled={disabled}
            tabIndex={
              checked || (value === null && !allowDefault && i === 0) ? 0 : -1
            }
            onClick={() => onChange(v)}
            onKeyDown={(e) => onKey(e, i)}
            className="glass-item flex min-h-11 flex-col gap-2 rounded-[20px] p-2 text-left text-sm"
          >
            <span
              aria-hidden="true"
              className="relative block h-12 w-full overflow-hidden rounded-[14px] bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)]"
            >
              {url && (
                <span
                  className="absolute inset-0 bg-[var(--nx-pattern)]"
                  style={{ maskImage: url, WebkitMaskImage: url }}
                />
              )}
            </span>
            <span
              className={cn(
                "self-start rounded-full px-2.5 py-0.5",
                checked && "bg-surface-strong text-bg",
              )}
            >
              {text}
            </span>
          </button>
        );
      })}
    </div>
  );
}
