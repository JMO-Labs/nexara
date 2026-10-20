"use client";
/**
 * @file components/ui/SettingsRow.tsx
 * @brief Two-column settings control layout (label left, input right on md+).
 * @param label Primary setting label
 * @param description Optional descriptive text below label
 * @param children Form control(s) to display
 */
import React, { type ReactNode } from "react";
import { Grid, Typography } from "@mui/joy";

export interface SettingsRowProps {
  label: string;
  description?: string;
  children: ReactNode;
}

export const SettingsRow = React.forwardRef<HTMLDivElement, SettingsRowProps>(
  function SettingsRow({ label, description, children }, ref) {
    return (
      <Grid
        ref={ref}
        container
        spacing={2}
        sx={{
          alignItems: "flex-start",
          py: 1.5,
          borderBottom: "1px solid var(--joy-palette-divider)",
        }}
      >
        <Grid xs={12} md={4}>
          <Typography level="body-sm" fontWeight="md">
            {label}
          </Typography>
          {description && (
            <Typography
              level="body-xs"
              sx={{ color: "text.tertiary", mt: 0.5 }}
            >
              {description}
            </Typography>
          )}
        </Grid>
        <Grid xs={12} md={8}>
          {children}
        </Grid>
      </Grid>
    );
  },
);

export default SettingsRow;
