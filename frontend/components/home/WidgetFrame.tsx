"use client";
/**
 * @file components/home/WidgetFrame.tsx
 * @brief Editorial chrome around a dashboard widget. Drag + resize are
 *        handled by react-grid-layout (the parent container). This frame
 *        only provides title, collapse toggle, and an optional remove
 *        button. Buttons match `.rgl-cancel` or `button` so RGL's
 *        `draggableCancel` selector keeps clicks from initiating drag.
 */
import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import Box from "@mui/joy/Box";
import { collapseTransition } from "@/components/ui/motion";
import { useConfirmDialog } from "@/stores/confirmDialog";

export interface WidgetFrameProps {
  title: string;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onRemove?: () => void;
  children: React.ReactNode;
  className?: string;
}

export function WidgetFrame({
  title,
  collapsed = false,
  onToggleCollapsed,
  onRemove,
  children,
  className,
}: WidgetFrameProps) {
  const prefersReduced = useReducedMotion();
  const transition = prefersReduced ? { duration: 0 } : collapseTransition;
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
        transition: "border-color 150ms, box-shadow 150ms",
        "&:hover": { borderColor: "neutral.300", boxShadow: "sm" },
        // Show a subtle move-cursor on the body so users discover dragging.
        cursor: "move",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          pt: 1.75,
          pb: 1,
          gap: 1,
          flexShrink: 0,
        }}
      >
        <Box
          component="h2"
          sx={{
            m: 0,
            fontSize: "11px",
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "text.tertiary",
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {title}
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 0.25, flexShrink: 0 }}>
          <button
            type="button"
            aria-label={collapsed ? "Expand widget" : "Collapse widget"}
            aria-expanded={!collapsed}
            aria-controls={panelId}
            onClick={(e) => {
              e.stopPropagation();
              onToggleCollapsed?.();
            }}
            className="rgl-cancel p-1 rounded-md text-[var(--nx-palette-text-tertiary)] hover:text-[var(--nx-palette-text-primary)] hover:bg-[var(--nx-palette-neutral-100)] transition-colors"
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
              <svg aria-hidden="true" width="13" height="13" viewBox="0 0 14 14">
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

      {/* Body — collapsible. flex:1 + minHeight:0 lets children scroll. */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            id={panelId}
            key="widget-body"
            initial={{ height: 0, overflow: "hidden" }}
            animate={{ height: "auto", overflow: "hidden", transition }}
            exit={{ height: 0, overflow: "hidden", transition }}
            style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}
          >
            <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", px: 2, pb: 2 }}>
              {children}
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
}

export default WidgetFrame;
