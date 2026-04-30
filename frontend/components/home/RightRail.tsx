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
import { WidgetGallery } from "./WidgetGallery";

interface RailTabProps {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  badge?: number;
  onClick: () => void;
}

function RailTab({ label, icon, active, badge, onClick }: RailTabProps) {
  // Collapsed rest state shows just the icon (40x40 puck). On hover or
  // focus the tab grows leftward and reveals the label.
  return (
    <Box
      component="button"
      type="button"
      onClick={onClick}
      aria-label={`${label}${badge ? ` (${badge} unread)` : ""}`}
      aria-pressed={active}
      sx={{
        all: "unset",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: 0,
        position: "relative",
        borderTopLeftRadius: 12,
        borderBottomLeftRadius: 12,
        pl: 1.25,
        pr: 1.25,
        py: 1,
        minHeight: 40,
        // Collapsed: tucked against right edge, icon only.
        width: 40,
        bgcolor: active ? "primary.500" : "background.surface",
        color: active ? "#fff" : "text.primary",
        border: "1px solid",
        borderColor: active ? "primary.500" : "divider",
        borderRight: "none",
        boxShadow: "sm",
        overflow: "hidden",
        transition:
          "width 200ms ease, gap 200ms ease, padding 200ms ease, background-color 150ms, color 150ms, box-shadow 150ms",
        "&:hover, &:focus-visible": {
          width: 132,
          gap: 8,
          pl: 1.5,
          boxShadow: "md",
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
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: active ? "#fff" : "primary.plainColor",
        }}
      >
        {icon}
      </Box>
      <Box
        component="span"
        sx={{
          flex: 1,
          minWidth: 0,
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          // Hidden in collapsed state; revealed by parent's hover.
          opacity: 0,
          transition: "opacity 150ms ease",
          "button:hover &, button:focus-visible &": { opacity: 1 },
        }}
      >
        {label}
      </Box>
      {typeof badge === "number" && badge > 0 && (
        <Box
          sx={{
            position: "absolute",
            top: 4,
            right: 4,
            bgcolor: active ? "rgba(255,255,255,0.25)" : "primary.500",
            color: "#fff",
            borderRadius: "xl",
            minWidth: 16,
            height: 16,
            px: 0.5,
            fontSize: 9,
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontVariantNumeric: "tabular-nums",
            // Pop into the row when expanded.
            "button:hover &, button:focus-visible &": {
              position: "relative",
              top: "auto",
              right: "auto",
            },
          }}
        >
          {badge > 99 ? "99+" : badge}
        </Box>
      )}
    </Box>
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
