/**
 * @file components/ui/page/Panel.tsx
 * @brief Glass panel with optional header (icon, title, actions).
 */
import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PanelProps extends Omit<
  React.HTMLAttributes<HTMLElement>,
  "title"
> {
  title?: string;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  as?: "section" | "div";
}

/**
 * @brief Glass surface.
 * @param props see PanelProps
 * @return section or div
 */
export function Panel({
  title,
  icon: Icon,
  actions,
  as: As = "section",
  className,
  children,
  ...rest
}: PanelProps) {
  return (
    <As className={cn("glass rounded-[32px] p-5", className)} {...rest}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title && (
            <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
              {Icon && <Icon className="size-4" aria-hidden="true" />}
              {title}
            </h2>
          )}
          {actions && (
            <div className="ml-auto flex items-center gap-2">{actions}</div>
          )}
        </div>
      )}
      {children}
    </As>
  );
}
