"use client";
/**
 * @file components/layout/PageMasthead.tsx
 * @brief Editorial page header — atmospheric backdrop, oversized Fraunces
 *        wordmark, hairline rule + uppercase metric line, optional right slot.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";

export interface PageMastheadProps {
  title: string;
  /** Small uppercase line to the right of the rule (e.g. "12 events this month"). */
  meta?: string;
  /** Optional slot rendered at right (button, action). */
  right?: React.ReactNode;
  /** Title scale — default "lg" matches galleries page. */
  size?: "md" | "lg";
}

const TITLE_SIZES = {
  md: { xs: "12vw", sm: "64px", md: "92px", lg: "116px" },
  lg: { xs: "14vw", sm: "88px", md: "120px", lg: "156px" },
} as const;

export function PageMasthead({
  title,
  meta,
  right,
  size = "lg",
}: PageMastheadProps) {
  return (
    <Box sx={{ position: "relative", mb: { xs: 2, md: 3 } }}>
      {/* Atmospheric backdrop — warm radial wash */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          inset: "-40px -40px 0 -40px",
          pointerEvents: "none",
          zIndex: 0,
          background:
            "radial-gradient(ellipse 1100px 480px at 18% -10%, var(--joy-palette-warning-softBg, rgba(217,164,87,0.18)) 0%, transparent 65%), radial-gradient(ellipse 800px 360px at 95% 8%, var(--joy-palette-primary-softBg, rgba(36,108,121,0.10)) 0%, transparent 70%)",
        }}
      />
      <Box
        sx={{
          position: "relative",
          zIndex: 1,
          pt: { xs: 3, md: 5 },
          pb: { xs: 2, md: 3 },
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          alignItems={{ md: "flex-end" }}
          justifyContent="space-between"
          spacing={2}
        >
          <Box>
            <Typography
              component="h1"
              sx={{
                fontFamily: "var(--font-display)",
                fontWeight: 400,
                fontSize: TITLE_SIZES[size],
                lineHeight: 0.88,
                letterSpacing: "-0.04em",
                color: "text.primary",
              }}
            >
              {title}
            </Typography>
            {meta && (
              <Stack
                direction="row"
                spacing={1.5}
                alignItems="center"
                sx={{ mt: 2 }}
              >
                <Box
                  sx={{
                    height: "1px",
                    width: 56,
                    background: "currentColor",
                    opacity: 0.35,
                  }}
                />
                <Typography
                  level="body-sm"
                  sx={{
                    fontFamily: "var(--font-mono, var(--font-body))",
                    fontSize: "11px",
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    color: "text.secondary",
                  }}
                >
                  {meta}
                </Typography>
              </Stack>
            )}
          </Box>
          {right && (
            <Box sx={{ alignSelf: { xs: "flex-start", md: "auto" } }}>
              {right}
            </Box>
          )}
        </Stack>
      </Box>
    </Box>
  );
}

export default PageMasthead;
