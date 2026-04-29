"use client";
/**
 * @file components/home/widgets/QuickActionsWidget.tsx
 * @brief Quick-action tiles: New post · New event · Upload media. Editorial
 *        palette — terracotta accent on hover, paper surface, clean icons.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import {
  PencilSquareIcon,
  CalendarDaysIcon,
  PhotoIcon,
} from "@heroicons/react/24/outline";
import { useModals } from "@/stores/modals";
import type { WidgetContext } from "@/lib/widgets/registry";

interface ActionTileProps {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}

function ActionTile({ label, icon, onClick }: ActionTileProps) {
  return (
    <Box
      component="button"
      type="button"
      aria-label={label}
      onClick={onClick}
      sx={{
        all: "unset",
        cursor: "pointer",
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 1,
        px: 1.5,
        py: 1.75,
        borderRadius: "md",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.surface",
        textAlign: "center",
        transition: "border-color 150ms, transform 150ms, color 150ms",
        color: "text.secondary",
        "&:hover": {
          borderColor: "primary.500",
          color: "primary.plainColor",
          transform: "translateY(-1px)",
        },
        "&:focus-visible": {
          outline: "2px solid var(--nx-palette-focusVisible)",
          outlineOffset: 2,
        },
      }}
    >
      <Box
        sx={{
          color: "primary.plainColor",
          width: 28,
          height: 28,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {icon}
      </Box>
      <Box
        sx={{
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.02em",
          color: "text.primary",
          lineHeight: 1.2,
        }}
      >
        {label}
      </Box>
    </Box>
  );
}

export function QuickActionsWidget(_: WidgetContext) {
  const show = useModals((s) => s.show);

  return (
    <Box sx={{ display: "flex", gap: 1, flexWrap: "nowrap" }}>
      <ActionTile
        label="New post"
        icon={<PencilSquareIcon aria-hidden width={20} height={20} />}
        onClick={() => show("create-post")}
      />
      <ActionTile
        label="Create event"
        icon={<CalendarDaysIcon aria-hidden width={20} height={20} />}
        onClick={() => show("create-event")}
      />
      <ActionTile
        label="Upload media"
        icon={<PhotoIcon aria-hidden width={20} height={20} />}
        onClick={() => show("create-gallery")}
      />
    </Box>
  );
}

export default QuickActionsWidget;
