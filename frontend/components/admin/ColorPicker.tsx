"use client";
/**
 * @file components/admin/ColorPicker.tsx
 * @brief Round native swatch + validated hex input, aligned on one row.
 */
import { Field, controlClass } from "@/components/ui/Field";
import { HEX_RE } from "@/lib/branding-palette";

export interface ColorPickerProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
}

/**
 * @brief Reusable color input with hex validation.
 * @param props label, value, change handler, optional extra error
 * @return picker
 */
export function ColorPicker({
  label,
  value,
  onChange,
  error,
}: ColorPickerProps) {
  const valid = HEX_RE.test(value);
  return (
    <Field label={label} error={valid ? error : "Use #RRGGBB format."}>
      {(a) => (
        <div className="flex items-center gap-3">
          <input
            type="color"
            aria-label={`${label} picker`}
            value={valid ? value.toLowerCase() : "#000000"}
            onChange={(e) => onChange(e.target.value)}
            className="size-10 shrink-0 cursor-pointer appearance-none overflow-hidden rounded-full border-0 bg-transparent p-0"
          />
          <input
            {...a}
            type="text"
            value={value}
            maxLength={7}
            className={controlClass + " h-10"}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      )}
    </Field>
  );
}
