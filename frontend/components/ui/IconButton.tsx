"use client";
/**
 * @file components/ui/IconButton.tsx
 * @brief Round icon-only button; aria-label is required and doubles as
 *        the hover/focus tooltip unless one is given (or `tooltip={false}`).
 */
import * as React from "react";
import { buttonVariants, type ButtonProps } from "./Button";
import { cn } from "@/lib/utils";
import { Tooltip } from "./Tooltip";

export type IconButtonProps = Omit<ButtonProps, "asChild" | "loading"> & {
  "aria-label": string;
  /**
   * Hover/focus tooltip text. Defaults to the aria-label so every icon
   * button explains itself; pass `false` to opt out.
   */
  tooltip?: string | false;
  /** Shortcut hint shown beside the tooltip text, e.g. "Ctrl+K". */
  shortcut?: string;
  tooltipSide?: "top" | "right" | "bottom" | "left";
};

const SQUARE = { sm: "size-8", md: "size-10", lg: "size-12" } as const;

/**
 * @brief Icon-only button.
 * @param props button props with required aria-label
 * @return button element
 */
export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton(
    {
      className,
      variant,
      size = "md",
      tooltip,
      shortcut,
      tooltipSide,
      ...rest
    },
    ref,
  ) {
    const button = (
      <button
        ref={ref}
        className={cn(
          buttonVariants({ variant, size, shape: "round" }),
          SQUARE[size ?? "md"],
          className,
        )}
        {...rest}
      />
    );
    const tip = tooltip === undefined ? rest["aria-label"] : tooltip;
    if (!tip) return button;
    return (
      <Tooltip
        side={tooltipSide}
        content={
          shortcut ? (
            <>
              {tip} <kbd className="ml-1 font-mono opacity-80">{shortcut}</kbd>
            </>
          ) : (
            tip
          )
        }
      >
        {button}
      </Tooltip>
    );
  },
);

export default IconButton;
