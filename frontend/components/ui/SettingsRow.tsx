/**
 * @file components/ui/SettingsRow.tsx
 * @brief Two-column settings layout (label left, control right on md+).
 */
import * as React from "react";

export interface SettingsRowProps {
  label: string;
  description?: string;
  children: React.ReactNode;
}

/**
 * @brief Settings row.
 * @param label primary label
 * @param description optional helper text
 * @param children control(s)
 * @return row element
 */
export const SettingsRow = React.forwardRef<HTMLDivElement, SettingsRowProps>(
  function SettingsRow({ label, description, children }, ref) {
    return (
      <div
        ref={ref}
        className="grid grid-cols-1 items-start gap-2 border-b border-ink/10 py-3 last:border-b-0 md:grid-cols-12 md:gap-4"
      >
        <div className="md:col-span-4">
          <p className="text-sm font-semibold">{label}</p>
          {description && (
            <p className="mt-0.5 text-xs text-muted">{description}</p>
          )}
        </div>
        <div className="md:col-span-8">{children}</div>
      </div>
    );
  },
);

export default SettingsRow;
