"use client";
/**
 * @file components/home/WidgetFrame.tsx
 * @brief Visual frame around a dashboard widget.
 *        Manages its own collapse via motion.div (no nested-button a11y issue).
 *        Provides title, collapse toggle, drag-handle slot, and optional remove button.
 * @param title             Widget heading text.
 * @param collapsed         Controlled collapsed state.
 * @param onToggleCollapsed Callback to flip collapsed state.
 * @param onRemove          If provided, shows a Remove button.
 * @param dragHandleSlot    Optional drag handle (passed from dnd-kit in P4).
 * @param size              Logical grid size; emitted as data-size attribute.
 * @param children          Widget body content.
 * @param className         Additional class names.
 */
import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Card } from "@/components/ui/Card";
import { collapseTransition } from "@/components/ui/motion";
import { useConfirmDialog } from "@/stores/confirmDialog";

export type WidgetSize = "sm" | "md" | "lg" | "full";

export interface WidgetFrameProps {
  title: string;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onRemove?: () => void;
  onSizeChange?: (size: WidgetSize) => void;
  currentSize?: WidgetSize;
  /** Slot for dnd-kit drag handle (P3/P4). */
  dragHandleSlot?: React.ReactNode;
  size?: WidgetSize;
  children: React.ReactNode;
  className?: string;
}

const SIZE_LABELS: Record<WidgetSize, string> = {
  sm: "S",
  md: "M",
  lg: "L",
  full: "F",
};

export function WidgetFrame({
  title,
  collapsed = false,
  onToggleCollapsed,
  onRemove,
  onSizeChange,
  currentSize,
  dragHandleSlot,
  size,
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
    <Card
      data-size={size}
      className={className}
      sx={{ p: 0, overflow: "hidden" }}
    >
      {/* Header row — all buttons are flat siblings, no nesting */}
      <div className="flex items-center justify-between w-full px-4 py-3">
        <div className="flex items-center gap-2">
          {dragHandleSlot}
          <h2
            className="text-sm font-semibold leading-none"
            style={{ color: "var(--joy-palette-text-primary)" }}
          >
            {title}
          </h2>
        </div>

        <div className="flex items-center gap-1">
          {/* Collapse toggle */}
          <button
            type="button"
            aria-label={collapsed ? "Expand widget" : "Collapse widget"}
            aria-expanded={!collapsed}
            aria-controls={panelId}
            onClick={(e) => { e.stopPropagation(); onToggleCollapsed?.(); }}
            className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] transition-colors"
          >
            <svg
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="currentColor"
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

          {/* Remove button */}
          {onRemove && (
            <button
              type="button"
              aria-label="Remove widget"
              onClick={handleRemove}
              className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-neutral-500 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] transition-colors"
            >
              <svg
                aria-hidden="true"
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="currentColor"
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
        </div>
      </div>

      {/* Collapsible body */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            id={panelId}
            key="widget-body"
            initial={{ height: 0, overflow: "hidden" }}
            animate={{ height: "auto", overflow: "hidden", transition }}
            exit={{ height: 0, overflow: "hidden", transition }}
          >
            <div className="px-4 pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Size controls — lower-left footer, always visible */}
      {onSizeChange && currentSize && (
        <div
          className="flex items-center gap-0.5 px-3 pb-2"
          onClick={(e) => e.stopPropagation()}
        >
          {(["sm", "md", "lg", "full"] as WidgetSize[]).map((s) => (
            <button
              key={s}
              type="button"
              aria-label={`Resize widget to ${s === "sm" ? "small" : s === "md" ? "medium" : s === "lg" ? "large" : "full"}`}
              aria-pressed={currentSize === s}
              onClick={(e) => { e.stopPropagation(); onSizeChange(s); }}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] ${
                currentSize === s
                  ? "bg-indigo-600 text-white"
                  : "bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:bg-neutral-200 dark:hover:bg-neutral-700"
              }`}
            >
              {SIZE_LABELS[s]}
            </button>
          ))}
        </div>
      )}
    </Card>
  );
}

export default WidgetFrame;
