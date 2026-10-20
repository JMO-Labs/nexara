"use client";
/**
 * @file components/auth/AuthCard.tsx
 * @brief Shared header + container for auth form pages.
 */
import type { ReactNode } from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";

export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Stack spacing={4}>
      <Box>
        <Typography level="h2" sx={{ fontFamily: "var(--font-display)" }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography level="body-md" color="neutral" sx={{ mt: 1 }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {children}
    </Stack>
  );
}
