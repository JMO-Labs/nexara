"use client";
/**
 * @file components/events/EventDetailPanel.tsx
 * @brief Bottom-anchored slide-up drawer for the events page. Independent of
 *        the main content layout (position: fixed, width tracks a container
 *        ref via ResizeObserver). Two snap heights, collapsed (~280px) and
 *        expanded (~82vh), toggled by the grab handle or dragging upward.
 *        Closes via Esc, outside click or the X button. Pieces live in
 *        ./event-detail/.
 */
import * as React from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import type { EventItem } from "@/lib/api/events";
import { useContainerRect } from "./event-detail/useContainerRect";
import { DrawerSurface } from "./event-detail/DrawerSurface";

const COLLAPSED_HEIGHT = 280;
const EXPANDED_VH = 0.82;

export interface EventDetailPanelProps {
  /**
   * Element whose width/left the drawer should track.
   * When omitted the panel spans the full viewport width.
   */
  containerRef?: React.RefObject<HTMLElement | null>;
  event: EventItem | null;
  subgroupNames: Map<string, string>;
  onClose: () => void;
  onEdit?: (event: EventItem) => void;
}

export function EventDetailPanel({
  containerRef,
  event,
  subgroupNames,
  onClose,
  onEdit,
}: EventDetailPanelProps) {
  const rect = useContainerRect(containerRef);
  const [expanded, setExpanded] = React.useState(false);
  const drawerRef = React.useRef<HTMLDivElement | null>(null);
  // Skip the very first outside-click after open (the click that selected
  // the event bubbles up after the drawer mounts).
  const armedRef = React.useRef(false);

  React.useEffect(() => {
    if (!event) {
      armedRef.current = false;
      return;
    }
    setExpanded(false);
    const armTimer = window.setTimeout(() => {
      armedRef.current = true;
    }, 0);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const onPointerDown = (e: PointerEvent) => {
      if (!armedRef.current) return;
      const node = drawerRef.current;
      if (node && !node.contains(e.target as Node)) {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.clearTimeout(armTimer);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointerDown);
    };
  }, [event, onClose]);

  const expandedPx =
    typeof window !== "undefined"
      ? Math.round(window.innerHeight * EXPANDED_VH)
      : 600;
  const targetHeight = expanded ? expandedPx : COLLAPSED_HEIGHT;

  const panel = (
    <AnimatePresence>
      {event && rect && (
        <motion.div
          key="event-detail-drawer"
          initial={{ y: COLLAPSED_HEIGHT + 40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: COLLAPSED_HEIGHT + 40, opacity: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 34 }}
          style={{
            position: "fixed",
            bottom: 0,
            left: rect.left,
            width: rect.width,
            zIndex: 30,
          }}
        >
          <DrawerSurface
            ref={drawerRef}
            event={event}
            subgroupNames={subgroupNames}
            onClose={onClose}
            onEdit={onEdit}
            expanded={expanded}
            setExpanded={setExpanded}
            targetHeight={targetHeight}
            collapsedHeight={COLLAPSED_HEIGHT}
            expandedHeight={expandedPx}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  if (typeof document === "undefined") return null;
  return createPortal(panel, document.body);
}

export default EventDetailPanel;
