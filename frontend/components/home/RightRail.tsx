"use client";
/**
 * @file components/home/RightRail.tsx
 * @brief Vertical stack of slide-out tabs affixed to the right edge of the
 *        viewport. Tracks pointer Y to apply a macOS-Dock-style zoom: the
 *        tab nearest the cursor scales + translates outward most, neighbors
 *        ease into the falloff so the rail feels like one connected ribbon.
 */
import * as React from "react";
import { usePathname } from "next/navigation";
import Box from "@mui/joy/Box";
import {
  ChatBubbleLeftRightIcon,
  AdjustmentsHorizontalIcon,
} from "@heroicons/react/24/outline";
import { useChatDock } from "@/stores/chatDock";
import { useDashboardRail } from "@/stores/dashboardRail";
import { Tooltip } from "@/components/ui/Tooltip";
import { WidgetGallery } from "./WidgetGallery";

interface RailTabProps {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  badge?: number;
  onClick: () => void;
  /** 0..1 — proximity weight from dock controller (1 = under cursor). */
  proximity: number;
  registerRef: (el: HTMLButtonElement | null) => void;
}

// Dock falloff curve: peak shift/scale at proximity=1, eases to 0 at edges.
const MAX_SCALE_BOOST = 0.45; // 1 -> 1.45 at peak (grows leftward from right edge)

function RailTab({
  label,
  icon,
  active,
  badge,
  onClick,
  proximity,
  registerRef,
}: RailTabProps) {
  const tooltipTitle =
    typeof badge === "number" && badge > 0
      ? `${label} (${badge} unread)`
      : label;
  const scale = 1 + proximity * MAX_SCALE_BOOST;
  return (
    <Tooltip title={tooltipTitle} placement="left" enterDelay={400}>
      <Box
        ref={registerRef}
        component="button"
        type="button"
        onClick={onClick}
        aria-label={tooltipTitle}
        aria-pressed={active}
        sx={{
          all: "unset",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          borderTopLeftRadius: 10,
          borderBottomLeftRadius: 10,
          py: 1,
          width: 32,
          minHeight: 40,
          bgcolor: active ? "primary.500" : "background.surface",
          color: active ? "#fff" : "text.primary",
          borderTop: "1px solid",
          borderBottom: "1px solid",
          borderLeft: "1px solid",
          borderColor: active ? "primary.500" : "divider",
          boxShadow:
            proximity > 0.05
              ? "0 8px 18px -6px rgba(0,0,0,0.28)"
              : "0 4px 12px -4px rgba(0,0,0,0.18)",
          transformOrigin: "right center",
          transform: `scale(${scale})`,
          zIndex: proximity > 0.05 ? Math.round(10 + proximity * 100) : 1,
          transition:
            "transform 140ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow 160ms ease, background-color 150ms, color 150ms",
          willChange: "transform",
          "&::before": {
            content: '""',
            position: "absolute",
            left: 3,
            top: "50%",
            transform: "translateY(-50%)",
            width: 2,
            height: 14,
            backgroundImage: active
              ? "radial-gradient(circle, rgba(255,255,255,0.85) 1px, transparent 1px)"
              : "radial-gradient(circle, var(--nx-palette-text-tertiary) 1px, transparent 1px)",
            backgroundSize: "2px 4px",
            backgroundRepeat: "repeat-y",
            opacity: 0.5 + proximity * 0.5,
            transition: "opacity 150ms ease",
          },
          "&:focus-visible": {
            outline: "2px solid var(--nx-palette-focusVisible)",
            outlineOffset: 2,
          },
        }}
      >
        <Box
          sx={{
            width: 16,
            height: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: active ? "#fff" : "primary.plainColor",
            ml: 0.5,
          }}
        >
          {icon}
        </Box>
        {typeof badge === "number" && badge > 0 && (
          <Box
            sx={{
              position: "absolute",
              top: 2,
              right: 2,
              bgcolor: active ? "rgba(255,255,255,0.3)" : "primary.500",
              color: "#fff",
              borderRadius: "xl",
              minWidth: 14,
              height: 14,
              px: 0.4,
              fontSize: 9,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {badge > 99 ? "99+" : badge}
          </Box>
        )}
      </Box>
    </Tooltip>
  );
}

// Cursor proximity in px where a tab still gets any zoom influence.
// Tighter than tab-height + gap so neighbors only get a faint nudge.
const INFLUENCE_RADIUS = 56;

export function RightRail() {
  const pathname = usePathname();
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const setLauncherOpen = useChatDock((s) => s.setLauncherOpen);
  const unread = useChatDock((s) => s.unreadCount);
  const customizeOpen = useDashboardRail((s) => s.customizeOpen);
  const setCustomizeOpen = useDashboardRail((s) => s.setCustomizeOpen);

  const onHome = pathname === "/app";
  const onChatRoute =
    pathname === "/app/chat" || pathname.startsWith("/app/chat/");

  const tabRefs = React.useRef<Array<HTMLButtonElement | null>>([]);
  const [proximities, setProximities] = React.useState<number[]>([]);

  const updateFromPointer = React.useCallback((clientY: number | null) => {
    const next = tabRefs.current.map((el) => {
      if (!el || clientY === null) return 0;
      const r = el.getBoundingClientRect();
      const center = r.top + r.height / 2;
      const d = Math.abs(clientY - center);
      if (d >= INFLUENCE_RADIUS) return 0;
      // Cosine falloff: smooth peak at center, 0 at radius.
      const t = 1 - d / INFLUENCE_RADIUS;
      return t * t * (3 - 2 * t); // smoothstep
    });
    setProximities((prev) => {
      if (
        prev.length === next.length &&
        prev.every((v, i) => Math.abs(v - next[i]) < 0.01)
      ) {
        return prev;
      }
      return next;
    });
  }, []);

  if (onChatRoute) return null;

  const tabs: Array<{
    key: string;
    label: string;
    icon: React.ReactNode;
    active: boolean;
    badge?: number;
    onClick: () => void;
  }> = [
    {
      key: "chat",
      label: "Chat",
      icon: <ChatBubbleLeftRightIcon width={16} />,
      active: launcherOpen,
      badge: unread,
      onClick: () => setLauncherOpen(!launcherOpen),
    },
  ];
  if (onHome) {
    tabs.push({
      key: "customize",
      label: "Customize",
      icon: <AdjustmentsHorizontalIcon width={16} />,
      active: customizeOpen,
      onClick: () => setCustomizeOpen(!customizeOpen),
    });
  }

  if (tabRefs.current.length !== tabs.length) {
    tabRefs.current = Array(tabs.length).fill(null);
  }

  return (
    <>
      <Box
        role="toolbar"
        aria-label="Dashboard tools"
        onPointerMove={(e) => updateFromPointer(e.clientY)}
        onPointerLeave={() => updateFromPointer(null)}
        sx={{
          position: "fixed",
          top: "50%",
          right: 0,
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          // Generous hit-zone so the dock reacts before the cursor reaches a tab.
          pl: 6,
          py: 4,
          gap: 1,
          zIndex: 1100,
          pointerEvents: "auto",
        }}
      >
        {tabs.map((t, i) => (
          <RailTab
            key={t.key}
            label={t.label}
            icon={t.icon}
            active={t.active}
            badge={t.badge}
            onClick={t.onClick}
            proximity={proximities[i] ?? 0}
            registerRef={(el) => {
              tabRefs.current[i] = el;
            }}
          />
        ))}
      </Box>

      {onHome && (
        <WidgetGallery
          open={customizeOpen}
          onClose={() => setCustomizeOpen(false)}
        />
      )}
    </>
  );
}

export default RightRail;
