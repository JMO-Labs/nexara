/**
 * @file components/ui/Skeleton.tsx
 * @brief Loading placeholder. Pulse only when motion is allowed.
 */
import * as React from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";

/** Fade variants: 0->1 on mount, 1->0 on exit (parent AnimatePresence). */
export const skeletonVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.15, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};

export type SkeletonProps = Omit<
  React.HTMLAttributes<HTMLDivElement>,
  "onAnimationStart" | "onAnimationEnd" | "onDrag" | "onDragStart" | "onDragEnd"
> & {
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
 * @return motion.div (fade skipped under prefers-reduced-motion)
 */
export function Skeleton({
  width = "100%",
  height = 16,
  rounded = "sm",
  className,
  style,
  ...rest
}: SkeletonProps) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      variants={skeletonVariants}
      initial={reduced ? false : "initial"}
      animate="animate"
      exit={reduced ? undefined : "exit"}
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
