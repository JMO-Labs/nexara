/**
 * @file components/ui/Skeleton.tsx
 * @brief Loading placeholder. Pulse only when motion is allowed.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

export type SkeletonProps = React.HTMLAttributes<HTMLDivElement> & {
  width?: number | string;
  height?: number | string;
  rounded?: "sm" | "md" | "lg" | "pill";
};

const rad = {
  sm: "rounded-md",
  md: "rounded-xl",
  lg: "rounded-[1.25rem]",
  pill: "rounded-full",
} as const;

/**
 * @brief Status-role placeholder block.
 * @param width css width (default 100%)
 * @param height css height (default 16)
 * @param rounded radius step
 * @return div
 */
export function Skeleton({
  width = "100%",
  height = 16,
  rounded = "sm",
  className,
  style,
  ...rest
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-live="polite"
      className={cn(
        "bg-muted/40 motion-safe:animate-pulse",
        rad[rounded],
        className,
      )}
      style={{ width, height, ...style }}
      {...rest}
    />
  );
}

export default Skeleton;
