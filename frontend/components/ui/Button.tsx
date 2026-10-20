"use client";
/**
 * @file components/ui/Button.tsx
 * @brief Tailwind button with cva variants, loading state and asChild.
 */
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** @brief Shared variant/size classes for Button and IconButton. */
export const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 font-semibold whitespace-nowrap transition-colors outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-surface-strong text-accent hover:opacity-90",
        secondary: "bg-accent text-surface-strong hover:opacity-90",
        ghost: "bg-transparent hover:bg-surface",
        outline: "border border-current bg-transparent hover:bg-surface",
        destructive: "bg-destructive text-white hover:opacity-90",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
      },
      shape: { rect: "rounded-xl", round: "rounded-full px-0" },
    },
    defaultVariants: { variant: "primary", size: "md", shape: "rect" },
  },
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  Omit<VariantProps<typeof buttonVariants>, "shape"> & {
    loading?: boolean;
    asChild?: boolean;
  };

/**
 * @brief Button primitive.
 * @param props native button props plus variant, size, loading, asChild
 * @return button element
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { className, variant, size, loading, asChild, disabled, children, ...rest },
    ref,
  ) {
    const Comp = asChild ? Slot.Root : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={disabled || loading}
        aria-busy={loading ? true : undefined}
        {...rest}
      >
        {asChild ? (
          children
        ) : (
          <>
            {loading && (
              <Loader2
                aria-hidden
                className="size-4 motion-safe:animate-spin"
              />
            )}
            {children}
          </>
        )}
      </Comp>
    );
  },
);

export default Button;
