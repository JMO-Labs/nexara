"use client";
/**
 * @file components/ui/Collapsible.tsx
 * @brief Animated collapsible section primitive.
 *        Uses framer-motion AnimatePresence + motion.div for height animation.
 *        Respects prefers-reduced-motion (instant toggle, no animation).
 */
import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

export interface CollapsibleProps {
  /** Controlled open state. */
  open: boolean;
  /** Callback when open state should change. */
  onOpenChange?: (open: boolean) => void;
  /** Header slot — rendered inside the toggle button. */
  header: React.ReactNode;
  children: React.ReactNode;
  headerProps?: { "aria-label"?: string };
  /** Animation duration in ms. Default 200. */
  motionDuration?: number;
}

/** Unique id counter for aria-controls pairing. */
let idCounter = 0;

export function Collapsible({
  open,
  onOpenChange,
  header,
  children,
  headerProps,
  motionDuration = 200,
}: CollapsibleProps) {
  const prefersReduced = useReducedMotion();
  const [panelId] = React.useState(() => `collapsible-panel-${++idCounter}`);
  const duration = prefersReduced ? 0 : motionDuration / 1000;

  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={headerProps?.["aria-label"]}
        onClick={() => onOpenChange?.(!open)}
        className="w-full text-left flex items-center justify-between focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)] rounded"
      >
        {header}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={panelId}
            key="collapsible-content"
            initial={{ height: 0, overflow: "hidden" }}
            animate={{
              height: "auto",
              overflow: "hidden",
              transition: { duration },
            }}
            exit={{ height: 0, overflow: "hidden", transition: { duration } }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Collapsible;
