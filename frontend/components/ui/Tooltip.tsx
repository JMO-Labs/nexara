"use client";
/**
 * @file components/ui/Tooltip.tsx
 * @brief Tooltip primitive with optional shortcut badge display.
 */
import { Tooltip as JoyTooltip, type TooltipProps } from "@mui/joy";
import { Box } from "@mui/joy";
import { forwardRef, type HTMLAttributes, type ReactNode } from "react";

/**
 * Anchor element used by JoyTooltip. Joy clones the child and injects an
 * `ownerState` prop; a plain DOM span warns. This forwardRef strips it.
 */
const TooltipAnchor = forwardRef<
  HTMLSpanElement,
  HTMLAttributes<HTMLSpanElement> & { ownerState?: unknown }
>(function TooltipAnchor({ ownerState: _ownerState, children, ...rest }, ref) {
  return (
    <span ref={ref} {...rest} style={{ display: "inline-flex", ...rest.style }}>
      {children}
    </span>
  );
});

export interface AppTooltipProps extends Omit<
  TooltipProps,
  "title" | "children"
> {
  title: ReactNode;
  shortcut?: string;
  children: ReactNode;
  disabled?: boolean;
}

export function Tooltip({
  title,
  shortcut,
  children,
  disabled,
  placement = "top",
  enterDelay = 400,
  enterNextDelay,
  ...rest
}: AppTooltipProps) {
  if (disabled) return <>{children}</>;
  // Default enterNextDelay to match enterDelay so each tooltip waits its own
  // delay instead of inheriting the shared shorter "next" timer.
  const nextDelay = enterNextDelay ?? enterDelay;
  const body = shortcut ? (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <span>{title}</span>
      <Box
        component="kbd"
        sx={{
          px: 0.5,
          py: 0.125,
          borderRadius: 4,
          fontSize: 11,
          bgcolor: "neutral.softBg",
          color: "neutral.softColor",
          fontFamily: "monospace",
        }}
      >
        {shortcut}
      </Box>
    </Box>
  ) : (
    title
  );
  return (
    <JoyTooltip
      title={body}
      placement={placement}
      enterDelay={enterDelay}
      enterNextDelay={nextDelay}
      leaveDelay={0}
      arrow
      variant="solid"
      color="neutral"
      {...rest}
    >
      <TooltipAnchor>{children}</TooltipAnchor>
    </JoyTooltip>
  );
}

export default Tooltip;
