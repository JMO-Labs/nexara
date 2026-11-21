/**
 * @file components/ui/Card.tsx
 * @brief Glass-item card surface.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

export type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  tone?: "default";
};

/**
 * @brief Surface container.
 * @param tone default (glass-item surface)
 * @return card element
 */
export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { tone = "default", className, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      data-tone={tone}
      className={cn("glass-item rounded-[24px] text-ink", className)}
      {...rest}
    />
  );
});

export default Card;
