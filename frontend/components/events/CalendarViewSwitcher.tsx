"use client";
/**
 * @file components/events/CalendarViewSwitcher.tsx
 * @brief Segmented control for switching between month/week/day/list views.
 *        Uses Joy ToggleButtonGroup with active indicator = 2px brand border-bottom.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import ToggleButtonGroup from "@mui/joy/ToggleButtonGroup";
import Button from "@mui/joy/Button";

export type CalendarView = "month" | "week" | "day" | "list";

export interface CalendarViewSwitcherProps {
  value: CalendarView;
  onChange: (view: CalendarView) => void;
}

export function CalendarViewSwitcher({
  value,
  onChange,
}: CalendarViewSwitcherProps) {
  return (
    <Box sx={{ mb: 2 }}>
      <ToggleButtonGroup
        value={value}
        onChange={(_, newValue) => {
          if (newValue !== null) {
            onChange(newValue as CalendarView);
          }
        }}
        sx={{
          gap: 0.5,
          "--ToggleButtonGroup-radius": "0px",
        }}
      >
        {(["month", "week", "day", "list"] as const).map((view) => (
          <Button
            key={view}
            value={view}
            variant={value === view ? "solid" : "plain"}
            sx={{
              px: 1.5,
              py: 0.75,
              fontSize: 13,
              fontWeight: 600,
              textTransform: "capitalize",
              borderRadius: 0,
              borderBottom:
                value === view ? "2px solid" : "2px solid transparent",
              borderColor: value === view ? "primary.solidBg" : "transparent",
              backgroundColor: value === view ? "transparent" : "transparent",
              color: value === view ? "primary.solidBg" : "text.secondary",
              transition: "all 150ms ease",
              "&:hover": {
                color: "primary.solidBg",
              },
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.solidBg",
                outlineOffset: "-2px",
              },
            }}
          >
            {view}
          </Button>
        ))}
      </ToggleButtonGroup>
    </Box>
  );
}

export default CalendarViewSwitcher;
