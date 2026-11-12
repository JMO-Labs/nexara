"use client";
/**
 * @file components/admin/FontPicker.tsx
 * @brief Font family dropdown with live preview.
 */
import { Option, Select } from "@/components/ui";
import { MONO_FONTS, SANS_FONTS } from "@/lib/branding-palette";

export interface FontPickerProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  kind: "sans" | "mono";
}

/**
 * @brief Font dropdown (Google Fonts subset + system fonts) with preview.
 * @param props label, value, handler, kind
 * @return picker
 */
export function FontPicker({ label, value, onChange, kind }: FontPickerProps) {
  const base = kind === "mono" ? MONO_FONTS : SANS_FONTS;
  const list = base.includes(value) ? base : [value, ...base];
  const fallback = kind === "mono" ? "monospace" : "system-ui, sans-serif";
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">{label}</span>
      <Select label={label} value={value} onValueChange={onChange}>
        {list.map((f) => (
          <Option key={f} value={f}>
            {f}
          </Option>
        ))}
      </Select>
      <p
        data-testid="font-preview"
        style={{ fontFamily: `${value}, ${fallback}` }}
        className="text-sm"
      >
        The quick brown fox jumps over the lazy dog
      </p>
    </div>
  );
}
