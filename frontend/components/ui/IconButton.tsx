"use client";
/**
 * @file components/ui/IconButton.tsx
 * @brief Round icon-only button; aria-label is required.
 */
import * as React from "react";
import { buttonVariants, type ButtonProps } from "./Button";
import { cn } from "@/lib/utils";

export type IconButtonProps = Omit<ButtonProps, "asChild" | "loading"> & {
  "aria-label": string;
};

const SQUARE = { sm: "size-8", md: "size-10", lg: "size-12" } as const;

/**
 * @brief Icon-only button.
 * @param props button props with required aria-label
 * @return button element
 */
export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ className, variant, size = "md", ...rest }, ref) {
    return (
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
  },
);

export default IconButton;
