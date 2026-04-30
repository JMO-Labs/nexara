"use client";
/**
 * @file components/home/RightRail.tsx
 * @brief Vertical stack of slide-out tabs affixed to the right edge of the
 *        viewport. Each tab toggles a right-side drawer (Chat / Customize).
 *        Tabs feature an icon + small horizontal label. Hover extends the
 *        tab outward for affordance. Customize tab is hidden outside /app.
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
}

function RailTab({ label, icon, active, badge, onClick }: RailTabProps) {
  // Icon-only puck flush against right edge. Hover peeks ~6px outward
  // and a delayed tooltip surfaces the label.
  const tooltipTitle =
    typeof badge === "number" && badge > 0
      ? `${label} (${badge} unread)`
      : label;
  return (
    <Tooltip title={tooltipTitle} placement="left" enterDelay={500}>
      <Box
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
          boxShadow: "0 4px 12px -4px rgba(0,0,0,0.18)",
          transform: "translateX(0)",
          transition:
            "transform 180ms ease, background-color 150ms, color 150ms, box-shadow 150ms",
          // Grab dots — vertical 3-dot indicator on inner-left edge.
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
            opacity: 0.6,
            transition: "opacity 150ms ease",
          },
          "&:hover, &:focus-visible": {
            transform: "translateX(-6px)",
            boxShadow: "0 6px 16px -4px rgba(0,0,0,0.25)",
          },
          "&:hover::before, &:focus-visible::before": { opacity: 1 },
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

export function RightRail() {
  const pathname = usePathname();
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const setLauncherOpen = useChatDock((s) => s.setLauncherOpen);
  const unread = useChatDock((s) => s.unreadCount);
  const customizeOpen = useDashboardRail((s) => s.customizeOpen);
  const setCustomizeOpen = useDashboardRail((s) => s.setCustomizeOpen);

  const onHome = pathname === "/app";
  // Hide rail entirely on the dedicated chat page (matches FloatingChatDock).
  const onChatRoute = pathname === "/app/chat" || pathname.startsWith("/app/chat/");

  if (onChatRoute) return null;

  return (
    <>
      <Box
        role="toolbar"
        aria-label="Dashboard tools"
        sx={{
          position: "fixed",
          top: "50%",
          right: 0,
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          // Tabs hug right edge so a hovered tab grows leftward
          // independently — siblings keep their collapsed width.
          alignItems: "flex-end",
          gap: 1,
          zIndex: 1100,
          pointerEvents: "auto",
        }}
      >
        <RailTab
          label="Chat"
          icon={<ChatBubbleLeftRightIcon width={16} />}
          active={launcherOpen}
          badge={unread}
          onClick={() => setLauncherOpen(!launcherOpen)}
        />
        {onHome && (
          <RailTab
            label="Customize"
            icon={<AdjustmentsHorizontalIcon width={16} />}
            active={customizeOpen}
            onClick={() => setCustomizeOpen(!customizeOpen)}
          />
        )}
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
