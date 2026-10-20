"use client";
/**
 * @file components/home/WidgetFrame.tsx
 * @brief Editorial-magazine chrome around a dashboard widget. Each widget
 *        is treated like a numbered column in a print broadsheet:
 *        - Italic Fraunces issue-number prefix in terracotta (01, 02…)
 *        - Display-serif title with a hair-rule that extends past it
 *        - Paper-grain wash behind content (subtle radial-gradient noise)
 *        - Left-edge accent bar that animates in on hover
 *        - Lift + warm shadow on hover; staggered fade-in on mount
 *        Drag + resize are handled by react-grid-layout in the parent;
 *        controls have `.rgl-cancel` so RGL ignores their pointer events.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import { useConfirmDialog } from "@/stores/confirmDialog";

export interface WidgetFrameProps {
  title: string;
  /** Display index (0-based). Rendered as a 2-digit issue number. */
  index?: number;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onRemove?: () => void;
  children: React.ReactNode;
  className?: string;
}

export function WidgetFrame({
  title,
  index = 0,
  collapsed = false,
  onToggleCollapsed,
  onRemove,
  children,
  className,
}: WidgetFrameProps) {
  const panelId = React.useId();
  const confirm = useConfirmDialog((s) => s.confirm);

  const handleRemove = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const ok = await confirm({
      title: `Remove "${title}" widget?`,
      message: "This widget will be removed from your dashboard.",
      confirmLabel: "Remove",
      tone: "danger",
    });
    if (ok) onRemove?.();
  };

  const issueNumber = String(index + 1).padStart(2, "0");
  // Stagger page-load reveal — capped so late widgets don't lag forever.
  const enterDelay = `${Math.min(index, 7) * 60}ms`;

  return (
    <Box
      className={`group/widget ${className ?? ""}`}
      sx={{
        position: "relative",
        height: "100%",
        bgcolor: "background.surface",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "lg",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        cursor: "move",
        transition:
          "transform 220ms cubic-bezier(0.22, 1, 0.36, 1), border-color 200ms, box-shadow 220ms",
        // Page-load reveal — staggered by index.
        opacity: 0,
        transform: "translateY(6px)",
        animation: `widget-rise 520ms ${enterDelay} cubic-bezier(0.22, 1, 0.36, 1) forwards`,
        "@keyframes widget-rise": {
          to: { opacity: 1, transform: "translateY(0)" },
        },
        "@media (prefers-reduced-motion: reduce)": {
          animation: "none",
          opacity: 1,
          transform: "none",
        },
        // Paper-grain wash — radial dot pattern at very low alpha.
        "&::before": {
          content: '""',
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          backgroundImage:
            "radial-gradient(circle at 1px 1px, var(--joy-palette-text-tertiary) 0.5px, transparent 0.5px)",
          backgroundSize: "12px 12px",
          opacity: 0.05,
          mixBlendMode: "multiply",
        },
        // Left-edge accent — terracotta bar that grows in on hover.
        "&::after": {
          content: '""',
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 2,
          bgcolor: "primary.500",
          transform: "scaleY(0)",
          transformOrigin: "top",
          transition: "transform 320ms cubic-bezier(0.22, 1, 0.36, 1)",
        },
        "&:hover": {
          transform: "translateY(-2px)",
          borderColor: "primary.200",
          boxShadow:
            "0 12px 28px -16px rgba(193, 90, 59, 0.32), 0 2px 8px -4px rgba(43, 42, 40, 0.12)",
          "&::after": { transform: "scaleY(1)" },
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          position: "relative",
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          px: 2,
          pt: 1.75,
          pb: 1.25,
          gap: 1,
          flexShrink: 0,
          // Hair rule under the header that extends past the title to the
          // right edge — magazine column rule.
          "&::after": {
            content: '""',
            position: "absolute",
            left: 16,
            right: 16,
            bottom: 0,
            height: "1px",
            backgroundImage:
              "linear-gradient(90deg, var(--joy-palette-divider) 0%, var(--joy-palette-divider) 60%, transparent 100%)",
          },
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "baseline",
            gap: 1,
            minWidth: 0,
            flex: 1,
          }}
        >
          <Box
            component="span"
            aria-hidden="true"
            sx={{
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontSize: "13px",
              fontWeight: 500,
              color: "primary.500",
              lineHeight: 1,
              letterSpacing: "0.02em",
              fontVariantNumeric: "lining-nums tabular-nums",
              flexShrink: 0,
              // Tiny vertical lift so the number sits with the cap-height.
              transform: "translateY(-1px)",
            }}
          >
            № {issueNumber}
          </Box>
          <Box
            component="h2"
            sx={{
              m: 0,
              fontFamily: "var(--font-display)",
              fontWeight: 500,
              fontSize: "16px",
              lineHeight: 1.15,
              letterSpacing: "-0.005em",
              color: "text.primary",
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {title}
          </Box>
        </Box>

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.25,
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            aria-label={collapsed ? "Expand widget" : "Collapse widget"}
            aria-expanded={!collapsed}
            aria-controls={panelId}
            onClick={(e) => {
              e.stopPropagation();
              onToggleCollapsed?.();
            }}
            className="rgl-cancel p-1 rounded-md text-[var(--nx-palette-text-tertiary)] hover:text-[var(--nx-palette-primary-500)] hover:bg-[var(--nx-palette-primary-50)] transition-colors"
          >
            <svg
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 14 14"
              className={`transition-transform ${collapsed ? "-rotate-90" : ""}`}
            >
              <path
                d="M2 4.5l5 5 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          {onRemove && (
            <button
              type="button"
              aria-label="Remove widget"
              onClick={handleRemove}
              className="rgl-cancel p-1 rounded-md text-[var(--nx-palette-text-tertiary)] hover:text-[var(--nx-palette-danger-500)] hover:bg-[var(--nx-palette-danger-50)] transition-colors opacity-0 md:group-hover/widget:opacity-100 focus-visible:opacity-100"
            >
              <svg
                aria-hidden="true"
                width="13"
                height="13"
                viewBox="0 0 14 14"
              >
                <path
                  d="M2 2l10 10M12 2L2 12"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  fill="none"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          )}
        </Box>
      </Box>

      {/* Body — sized by the parent GridItem (h grid units * row height).
          When collapsed, the GridItem is forced to h=1 so the body is
          clipped behind the header; we hide it via display so its
          intrinsic height doesn't fight RGL's row-height math. */}
      <Box
        id={panelId}
        sx={{
          position: "relative",
          flex: 1,
          minHeight: 0,
          display: collapsed ? "none" : "flex",
          flexDirection: "column",
          overflow: "auto",
          px: 2,
          pt: 1.5,
          pb: 2,
        }}
      >
        {children}
      </Box>
    </Box>
  );
}

export default WidgetFrame;
