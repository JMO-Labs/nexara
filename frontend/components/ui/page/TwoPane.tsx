/**
 * @file components/ui/page/TwoPane.tsx
 * @brief Aside + main layout: grid at md+, stacked on phone.
 */
import * as React from "react";

export interface TwoPaneProps {
  aside: React.ReactNode;
  children: React.ReactNode;
  asideWidth?: number;
}

/**
 * @brief Two-pane layout.
 * @param asideWidth aside column width in px at md+ (default 300)
 * @return grid div
 */
export function TwoPane({ aside, children, asideWidth = 300 }: TwoPaneProps) {
  return (
    <div
      data-slot="two-pane"
      style={{ "--aside-w": `${asideWidth}px` } as React.CSSProperties}
      className="grid gap-4 md:grid-cols-[var(--aside-w)_minmax(0,1fr)] md:gap-[18px]"
    >
      <aside className="min-w-0 md:sticky md:top-4 md:self-start">
        {aside}
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
