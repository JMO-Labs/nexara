"use client";
/**
 * @file components/home/WidgetFrame.tsx
 * @brief Visual frame around a dashboard widget.
 *        Wraps Card + Collapsible; provides title, collapse toggle,
 *        drag-handle slot, and optional remove button.
 * @param title           Widget heading text.
 * @param collapsed       Controlled collapsed state.
 * @param onToggleCollapsed Callback to flip collapsed state.
 * @param onRemove        If provided, shows a Remove button.
 * @param dragHandleSlot  Optional drag handle (passed from dnd-kit in P4).
 * @param size            Logical grid size; emitted as data-size attribute.
 * @param children        Widget body content.
 * @param className       Additional class names.
 */
import * as React from "react";
import { Card } from "@/components/ui/Card";
import { Collapsible } from "@/components/ui/Collapsible";

export interface WidgetFrameProps {
  title: string;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onRemove?: () => void;
  /** Slot for dnd-kit drag handle (P3/P4). */
  dragHandleSlot?: React.ReactNode;
  size?: "sm" | "md" | "lg" | "full";
  children: React.ReactNode;
  className?: string;
}

export function WidgetFrame({
  title,
  collapsed = false,
  onToggleCollapsed,
  onRemove,
  dragHandleSlot,
  size,
  children,
  className,
}: WidgetFrameProps) {
  const handleRemove = () => {
    // TODO: swap window.confirm for a nicer modal in polish phase
    if (window.confirm(`Remove "${title}" widget?`)) {
      onRemove?.();
    }
  };

  const header = (
    <div className="flex items-center justify-between w-full px-4 py-3">
      <div className="flex items-center gap-2">
        {dragHandleSlot}
        <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 leading-none">
          {title}
        </h2>
      </div>

      <div className="flex items-center gap-1">
        {/* Collapse toggle */}
        <button
          type="button"
          aria-label={collapsed ? "Expand widget" : "Collapse widget"}
          aria-expanded={!collapsed}
          onClick={(e) => {
            e.stopPropagation();
            onToggleCollapsed?.();
          }}
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
            onClick={(e) => {
              e.stopPropagation();
              handleRemove();
            }}
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
  );

  return (
    <Card
      data-size={size}
      className={className}
      sx={{ p: 0, overflow: "hidden" }}
    >
      <Collapsible
        open={!collapsed}
        onOpenChange={(isOpen) => {
          if (!isOpen !== collapsed) onToggleCollapsed?.();
        }}
        header={header}
      >
        <div className="px-4 pb-4">{children}</div>
      </Collapsible>
    </Card>
  );
}

export default WidgetFrame;
