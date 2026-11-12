"use client";
/**
 * @file components/admin/ColorPicker.tsx
 * @brief Native swatch + validated hex input.
 */
import { Input } from "@/components/ui";
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
    <div className="flex items-end gap-3">
      <input
        type="color"
        aria-label={`${label} picker`}
        value={valid ? value.toLowerCase() : "#000000"}
        onChange={(e) => onChange(e.target.value)}
        className="size-11 shrink-0 cursor-pointer rounded-xl"
      />
      <div className="flex-1">
        <Input
          label={label}
          value={value}
          maxLength={7}
          error={valid ? error : "Use #RRGGBB format."}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}
