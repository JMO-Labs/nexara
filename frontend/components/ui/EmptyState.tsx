"use client";
/**
 * @file components/ui/EmptyState.tsx
 * @brief Empty state with optional illustration slot. Display title in
 *        Fraunces, body copy in Geist, primary action button. Used by
 *        feed/galleries/events/search "nothing yet" surfaces.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import { motion } from "framer-motion";
import { fadeSlide } from "./motion";

export interface EmptyStateProps {
  illustration?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  compact?: boolean;
}

export function EmptyState({
  illustration,
  title,
  description,
  action,
  compact,
}: EmptyStateProps) {
  return (
    <motion.div variants={fadeSlide} initial="hidden" animate="show">
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          gap: 2,
          py: compact ? 4 : 8,
          px: 3,
          color: "text.secondary",
        }}
      >
        {illustration && (
          <Box
            sx={{
              width: compact ? 96 : 160,
              height: compact ? 96 : 160,
              opacity: 0.9,
            }}
          >
            {illustration}
          </Box>
        )}
        <Typography
          level={compact ? "h4" : "h3"}
          sx={{ fontFamily: "var(--font-display)", color: "text.primary" }}
        >
          {title}
        </Typography>
        {description && (
          <Typography level="body-md" sx={{ maxWidth: 420 }}>
            {description}
          </Typography>
        )}
        {action && <Box sx={{ mt: 1 }}>{action}</Box>}
      </Box>
    </motion.div>
  );
}

export default EmptyState;
