"use client";
/**
 * @file components/events/event-form/ColorField.tsx
 * @brief Event colour swatch picker with default and custom options.
 */
import { EVENT_COLOR_PRESETS } from "../eventColors";
import { cn } from "@/lib/utils";

export interface ColorFieldProps {
  value: string | null;
  onChange: (next: string | null) => void;
}

const swatch =
  "size-7 rounded-full border-2 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

/**
 * @brief Swatch row; null means default colour.
 * @param props value and change handler
 * @return fieldset element
 */
export function ColorField({ value, onChange }: ColorFieldProps) {
  return (
    <fieldset className="flex flex-wrap items-center gap-2">
      <legend className="mb-1.5 text-sm font-semibold">Color</legend>
      <button
        type="button"
        aria-label="Default (no override)"
        aria-pressed={value === null}
        onClick={() => onChange(null)}
        className={cn(
          swatch,
          "bg-bg",
          value === null ? "border-ink" : "border-current/30",
        )}
      />
      {EVENT_COLOR_PRESETS.map((p) => (
        <button
          key={p.value}
          type="button"
          aria-label={p.name}
          aria-pressed={value === p.value}
          title={p.name}
          onClick={() => onChange(p.value)}
          className={cn(
            swatch,
            value === p.value ? "border-ink" : "border-transparent",
          )}
          style={{ backgroundColor: p.value }}
        />
      ))}
      <label className="ml-1 inline-flex cursor-pointer items-center gap-1 text-xs opacity-70">
        <input
          type="color"
          aria-label="Custom color"
          value={value ?? "#1f6feb"}
          onChange={(e) => onChange(e.target.value)}
          className="size-7 cursor-pointer border-none bg-transparent p-0"
        />
        Custom
      </label>
    </fieldset>
  );
}

export default ColorField;
