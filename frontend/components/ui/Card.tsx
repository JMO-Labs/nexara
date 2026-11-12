/**
 * @file components/ui/Card.tsx
 * @brief Garden Club card. `featured` uses the sharp-corner leaf shape.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

export type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  tone?: "default" | "featured";
};

/**
 * @brief Surface container.
 * @param tone default (surface) or featured (strong surface, leaf corner)
 * @return card element
 */
export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { tone = "default", className, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        tone === "featured"
          ? "bg-surface-strong text-bg corner-leaf"
          : "bg-surface text-ink rounded-[1.25rem]",
        className,
      )}
      {...rest}
    />
  );
});

export default Card;
