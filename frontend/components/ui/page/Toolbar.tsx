/**
 * @file components/ui/page/Toolbar.tsx
 * @brief Glass pill row for filters/search/actions; wraps on phone.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

export type ToolbarProps = React.HTMLAttributes<HTMLDivElement>;

/**
 * @brief Toolbar row.
 * @param props div props
 * @return div element
 */
export function Toolbar({ className, ...rest }: ToolbarProps) {
  return (
    <div
      className={cn(
        "glass mb-4 flex flex-wrap items-center gap-2 rounded-full p-1.5 md:mb-[18px]",
        className,
      )}
      {...rest}
    />
  );
}
