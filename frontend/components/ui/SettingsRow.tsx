/**
 * @file components/ui/SettingsRow.tsx
 * @brief Two-column settings layout: fixed label column, control fills the rest (md+).
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
        className="grid grid-cols-1 gap-2 border-b border-[var(--nx-glass-edge)] py-4 last:border-b-0 md:grid-cols-[15rem_minmax(0,1fr)] md:items-center md:gap-8"
      >
        <div className="min-w-0">
          <p className="text-sm font-semibold">{label}</p>
          {description && (
            <p className="mt-0.5 text-xs leading-relaxed text-muted">
              {description}
            </p>
          )}
        </div>
        <div className="min-w-0">{children}</div>
      </div>
    );
  },
);

export default SettingsRow;
