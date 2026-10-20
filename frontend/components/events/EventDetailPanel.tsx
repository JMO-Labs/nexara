"use client";
/**
 * @file components/events/EventDetailPanel.tsx
 * @brief Bottom-anchored slide-up drawer for the events page. Independent of
 *        the main content layout (position: fixed, width tracks a container
 *        ref via ResizeObserver). Two snap heights — collapsed (~280px) and
 *        expanded (~82vh) — toggled by clicking the grab handle or dragging
 *        upward. Closes via Esc or the X button.
 */
import * as React from "react";
import { createPortal } from "react-dom";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Link from "@mui/joy/Link";
import {
  motion,
  AnimatePresence,
  useMotionValue,
  animate,
} from "framer-motion";
import { format, parseISO } from "date-fns";
import {
  XMarkIcon,
  MapPinIcon,
  CalendarDaysIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  PencilSquareIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon,
} from "@heroicons/react/24/outline";
import { IconButton, Markdown } from "@/components/ui";
import { RsvpInline } from "./RsvpInline";
import type { EventItem } from "@/lib/api/events";
import { mapsUrlForCoords } from "@/lib/geo/openInMaps";
import dynamic from "next/dynamic";
import { toneForEvent } from "./eventColors";
import { useDeleteEvent } from "@/hooks/useEvents";
import { useSession } from "@/stores/session";

const EventMiniMap = dynamic(
  () => import("./EventMiniMap").then((m) => m.EventMiniMap),
  { ssr: false, loading: () => null },
);

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

function useContainerRect(
  ref: React.RefObject<HTMLElement | null> | undefined,
) {
  const [rect, setRect] = React.useState<{
    left: number;
    width: number;
  } | null>(null);
  React.useEffect(() => {
    if (!ref) {
      // No ref — use full viewport width
      const update = () => setRect({ left: 0, width: window.innerWidth });
      update();
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const r = el.getBoundingClientRect();
      setRect({ left: r.left, width: r.width });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      ro.disconnect();
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [ref]);
  return rect;
}

function formatRange(starts: string, ends: string, allDay: boolean): string {
  const s = parseISO(starts);
  const e = parseISO(ends);
  const sDate = format(s, "EEE, MMM d, yyyy");
  if (allDay) {
    const eDate = format(e, "EEE, MMM d, yyyy");
    return sDate === eDate ? `${sDate} · All day` : `${sDate} → ${eDate}`;
  }
  const sameDay = format(s, "yyyy-MM-dd") === format(e, "yyyy-MM-dd");
  if (sameDay)
    return `${sDate} · ${format(s, "h:mm a")} – ${format(e, "h:mm a")}`;
  return `${sDate} ${format(s, "h:mm a")} → ${format(e, "EEE, MMM d")} ${format(e, "h:mm a")}`;
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

const DrawerSurface = React.forwardRef<
  HTMLDivElement,
  {
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
    const controls = animate(heightMV, targetHeight, {
      type: "spring",
      stiffness: 300,
      damping: 32,
    });
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
      const next = Math.min(
        expandedHeight,
        Math.max(140, dragStartHeight.current - dy),
      );
      heightMV.set(next);
    };
    const up = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const finalH = heightMV.get();
      const midpoint = (collapsedHeight + expandedHeight) / 2;
      const dy = ev.clientY - startY;
      // Tap (no real drag) → toggle
      if (Math.abs(dy) < 4) {
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
    <Box
      ref={ref}
      component={motion.div}
      style={{ height: heightMV }}
      sx={{
        backgroundColor: "background.surface",
        border: "1px solid",
        borderColor: "divider",
        borderBottom: "none",
        borderTopLeftRadius: 12,
        borderTopRightRadius: 12,
        boxShadow: "0 -16px 40px rgba(0,0,0,0.18)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
      role="region"
      aria-label="Event details"
    >
      {/* Tone strip */}
      <Box sx={{ height: 4, backgroundColor: tone.solid, flexShrink: 0 }} />

      {/* Drag handle */}
      <Box
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
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 18,
          cursor: "ns-resize",
          touchAction: "none",
          userSelect: "none",
          flexShrink: 0,
          "&:hover > div": { backgroundColor: "text.secondary" },
          "&:focus-visible": {
            outline: "2px solid",
            outlineColor: "primary.solidBg",
            outlineOffset: "-2px",
          },
        }}
      >
        <Box
          sx={{
            width: 44,
            height: 4,
            borderRadius: 2,
            backgroundColor: "text.tertiary",
            transition: "background-color 120ms ease",
          }}
        />
      </Box>

      <Stack
        direction="row"
        alignItems="flex-start"
        justifyContent="space-between"
        spacing={2}
        sx={{ px: { xs: 2, md: 3 }, pt: 0.5, pb: 1.5, flexShrink: 0 }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography
            level="body-xs"
            sx={{
              color: tone.onSoft,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.16em",
              mb: 0.5,
            }}
          >
            {tone.label}
          </Typography>
          <Typography
            level="h3"
            sx={{
              fontFamily: "var(--font-display)",
              lineHeight: 1.1,
              wordBreak: "break-word",
            }}
          >
            {event.title}
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.5} sx={{ flexShrink: 0 }}>
          {canEdit && onEdit && (
            <IconButton
              size="sm"
              variant="plain"
              aria-label="Edit event"
              onClick={() => onEdit(event)}
            >
              <PencilSquareIcon width={18} />
            </IconButton>
          )}
          {canEdit && (
            <IconButton
              size="sm"
              variant="plain"
              color="danger"
              aria-label="Delete event"
              onClick={onDelete}
              disabled={del.isPending}
            >
              <TrashIcon width={18} />
            </IconButton>
          )}
          <IconButton
            size="sm"
            variant="plain"
            aria-label={expanded ? "Collapse" : "Expand"}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronDownIcon width={18} />
            ) : (
              <ChevronUpIcon width={18} />
            )}
          </IconButton>
          <IconButton
            size="sm"
            variant="plain"
            aria-label="Close"
            onClick={onClose}
          >
            <XMarkIcon width={18} />
          </IconButton>
        </Stack>
      </Stack>

      <Box
        sx={{
          px: { xs: 2, md: 3 },
          pb: 2,
          overflowY: "auto",
          flex: 1,
          minHeight: 0,
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={{ xs: 1, md: 4 }}
          sx={{ mb: 1.5 }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <CalendarDaysIcon width={16} />
            <Typography level="body-sm">
              {formatRange(event.starts_at, event.ends_at, event.is_all_day)}
            </Typography>
          </Stack>
          {event.location && (
            <Stack direction="row" spacing={1} alignItems="center">
              <MapPinIcon width={16} />
              <Typography level="body-sm">{event.location}</Typography>
              {event.latitude != null && event.longitude != null && (
                <Link
                  href={mapsUrlForCoords(event.latitude, event.longitude)}
                  target="_blank"
                  rel="noopener noreferrer"
                  level="body-xs"
                  endDecorator={<ArrowTopRightOnSquareIcon width={12} />}
                  sx={{ ml: 0.5 }}
                >
                  Open in Google Maps
                </Link>
              )}
            </Stack>
          )}
        </Stack>
        {event.latitude != null && event.longitude != null && (
          <Box sx={{ mb: 2, maxWidth: 480 }}>
            <EventMiniMap
              lat={event.latitude}
              lon={event.longitude}
              height={180}
            />
          </Box>
        )}

        {event.description && (
          <Box
            sx={{
              color: "text.secondary",
              mb: 2,
              maxWidth: "72ch",
              fontSize: "0.875rem",
            }}
          >
            <Markdown content={event.description} size="sm" />
          </Box>
        )}

        <RsvpInline
          eventId={event.id}
          labels={event.rsvp_labels}
          current={event.user_rsvp?.status ?? null}
          counts={event.rsvp_counts}
        />

        {event.contribution_slots.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography
              level="body-xs"
              textColor="text.tertiary"
              sx={{
                textTransform: "uppercase",
                letterSpacing: "0.14em",
                fontWeight: 600,
                mb: 0.75,
              }}
            >
              Contributions
            </Typography>
            <Stack spacing={0.5}>
              {event.contribution_slots.map((slot) => (
                <Stack
                  key={slot.id ?? slot.title}
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{
                    px: 1,
                    py: 0.75,
                    borderRadius: "sm",
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography level="body-sm">{slot.title}</Typography>
                  <Typography
                    level="body-xs"
                    textColor="text.tertiary"
                    sx={{ fontVariantNumeric: "tabular-nums" }}
                  >
                    {slot.quantity_claimed} / {slot.quantity_needed}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Box>
        )}
      </Box>
    </Box>
  );
});

export default EventDetailPanel;
