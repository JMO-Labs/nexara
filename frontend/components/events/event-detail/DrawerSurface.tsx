"use client";
/**
 * @file components/events/event-detail/DrawerSurface.tsx
 * @brief Resizable bottom-sheet surface: tone strip, drag handle, header
 *        actions and body. Height springs between collapsed/expanded snaps.
 */
import * as React from "react";
import { motion, useMotionValue, animate } from "framer-motion";
import { X, Pencil, Trash2, ChevronUp, ChevronDown } from "lucide-react";
import { IconButton } from "@/components/ui";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent } from "../eventColors";
import { useDeleteEvent } from "@/hooks/useEvents";
import { useSession } from "@/stores/session";
import { EventDetailBody } from "./EventDetailBody";

export interface DrawerSurfaceProps {
  event: EventItem;
  subgroupNames: Map<string, string>;
  onClose: () => void;
  onEdit?: (event: EventItem) => void;
  expanded: boolean;
  setExpanded: (v: boolean) => void;
  targetHeight: number;
  collapsedHeight: number;
  expandedHeight: number;
}

/**
 * @brief Panel surface with drag-to-resize handle.
 * @param props see DrawerSurfaceProps
 * @return region element
 */
export const DrawerSurface = React.forwardRef<
  HTMLDivElement,
  DrawerSurfaceProps
>(function DrawerSurface(
  {
    event,
    subgroupNames,
    onClose,
    onEdit,
    expanded,
    setExpanded,
    targetHeight,
    collapsedHeight,
    expandedHeight,
  },
  ref,
) {
  const tone = toneForEvent(event, subgroupNames);
  const me = useSession((s) => s.user);
  const del = useDeleteEvent();
  const canEdit = !!me && me.id === event.author_id;
  const onDelete = () => {
    if (!confirm("Delete this event?")) return;
    del.mutate(event.id, { onSuccess: onClose });
  };
  const heightMV = useMotionValue(targetHeight);

  React.useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const controls = animate(
      heightMV,
      targetHeight,
      reduce
        ? { duration: 0 }
        : { type: "spring", stiffness: 300, damping: 32 },
    );
    return controls.stop;
  }, [targetHeight, heightMV]);

  // Drag the handle to resize. Negative dy = grow.
  const dragStartHeight = React.useRef(targetHeight);
  const onHandlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    dragStartHeight.current = heightMV.get();
    const startY = e.clientY;
    const move = (ev: PointerEvent) => {
      const dy = ev.clientY - startY;
      heightMV.set(
        Math.min(expandedHeight, Math.max(140, dragStartHeight.current - dy)),
      );
    };
    const up = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const finalH = heightMV.get();
      const midpoint = (collapsedHeight + expandedHeight) / 2;
      if (Math.abs(ev.clientY - startY) < 4) {
        setExpanded(!expanded);
        return;
      }
      if (finalH < 180) {
        onClose();
        return;
      }
      setExpanded(finalH >= midpoint);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  return (
    <motion.div
      ref={ref}
      style={{ height: heightMV }}
      className="flex flex-col overflow-hidden rounded-t-[1.25rem] border border-b-0 border-ink/15 bg-surface text-ink shadow-[0_-16px_40px_rgba(0,0,0,0.18)]"
      role="region"
      aria-label="Event details"
    >
      <div className="h-1 shrink-0" style={{ backgroundColor: tone.solid }} />
      <div
        onPointerDown={onHandlePointerDown}
        role="slider"
        aria-label={expanded ? "Collapse details" : "Expand details"}
        aria-valuenow={expanded ? expandedHeight : collapsedHeight}
        aria-valuemin={collapsedHeight}
        aria-valuemax={expandedHeight}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setExpanded(true);
          } else if (e.key === "ArrowDown") {
            e.preventDefault();
            if (expanded) setExpanded(false);
            else onClose();
          } else if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded(!expanded);
          }
        }}
        className="group flex h-[18px] shrink-0 cursor-ns-resize touch-none items-center justify-center select-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent"
      >
        <div className="h-1 w-11 rounded-full bg-muted transition-colors group-hover:bg-ink" />
      </div>
      <div className="flex shrink-0 items-start justify-between gap-4 px-4 pt-1 pb-3 md:px-6">
        <div className="min-w-0">
          <p
            className="mb-1 text-xs font-bold tracking-widest"
            style={{ color: tone.onSoft }}
          >
            {tone.label}
          </p>
          <h2 className="font-display text-2xl leading-tight break-words">
            {event.title}
          </h2>
        </div>
        <div className="flex shrink-0 gap-1">
          {canEdit && onEdit && (
            <IconButton
              size="sm"
              variant="ghost"
              aria-label="Edit event"
              onClick={() => onEdit(event)}
            >
              <Pencil className="size-[18px]" aria-hidden="true" />
            </IconButton>
          )}
          {canEdit && (
            <IconButton
              size="sm"
              variant="ghost"
              className="text-destructive"
              aria-label="Delete event"
              onClick={onDelete}
              disabled={del.isPending}
            >
              <Trash2 className="size-[18px]" aria-hidden="true" />
            </IconButton>
          )}
          <IconButton
            size="sm"
            variant="ghost"
            aria-label={expanded ? "Collapse" : "Expand"}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronDown className="size-[18px]" aria-hidden="true" />
            ) : (
              <ChevronUp className="size-[18px]" aria-hidden="true" />
            )}
          </IconButton>
          <IconButton
            size="sm"
            variant="ghost"
            aria-label="Close"
            onClick={onClose}
          >
            <X className="size-[18px]" aria-hidden="true" />
          </IconButton>
        </div>
      </div>
      <EventDetailBody event={event} />
    </motion.div>
  );
});

export default DrawerSurface;
