/**
 * @file components/ui/EmptyState.tsx
 * @brief "Nothing yet" block: optional icon/illustration, title, text, action.
 */
import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  icon?: LucideIcon;
  illustration?: React.ReactNode;
  compact?: boolean;
}

/**
 * @brief Centered empty state.
 * @param title heading text
 * @param description supporting copy
 * @param action node such as a Button
 * @param icon Lucide icon component
 * @return section
 */
export function EmptyState({
  title,
  description,
  action,
  icon: Icon,
  illustration,
  compact,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 px-6 text-center text-ink",
        compact ? "py-8" : "py-16",
      )}
    >
      {illustration ??
        (Icon && <Icon className="size-10 text-leaf" aria-hidden="true" />)}
      <h3
        className={cn(
          "font-black tracking-tight",
          compact ? "text-lg" : "text-2xl",
        )}
      >
        {title}
      </h3>
      {description && (
        <p className="max-w-md text-sm opacity-80">{description}</p>
      )}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}

export default EmptyState;
