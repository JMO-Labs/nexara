"use client";
/**
 * @file components/home/WelcomeBanner.tsx
 * @brief Editorial welcome banner. Warm Editorial palette (paper / ink /
 *        terracotta), display serif greeting, tabular-nums stat chips, and
 *        a subtle terracotta accent line.
 */
import * as React from "react";
import Link from "next/link";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import { Skeleton } from "@/components/ui/Skeleton";

export interface WelcomeBannerProps {
  userName: string;
  newPosts: number;
  upcomingEvents: number;
  unreadNotifications: number;
  isLoading?: boolean;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function getDateLabel(): string {
  return new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

interface StatChipProps {
  count: number;
  label: string;
  href: string;
  ariaLabel: string;
}

function StatChip({ count, label, href, ariaLabel }: StatChipProps) {
  const displayed = count > 99 ? "99+" : String(count);
  return (
    <Link
      href={href}
      aria-label={ariaLabel}
      className="group focus-visible:outline-none"
    >
      <Box
        sx={{
          display: "inline-flex",
          alignItems: "baseline",
          gap: 1,
          px: 1.75,
          py: 1,
          borderRadius: "md",
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.surface",
          transition: "border-color 150ms, transform 150ms",
          "&:hover": {
            borderColor: "primary.500",
            transform: "translateY(-1px)",
          },
          ".group:focus-visible &": {
            outline: "2px solid var(--nx-palette-focusVisible)",
            outlineOffset: "2px",
          },
        }}
      >
        <Typography
          level="title-md"
          sx={{
            fontVariantNumeric: "tabular-nums",
            color: "text.primary",
            fontWeight: 600,
          }}
        >
          {displayed}
        </Typography>
        <Typography level="body-xs" textColor="text.secondary">
          {label}
        </Typography>
      </Box>
    </Link>
  );
}

export function WelcomeBanner({
  userName,
  newPosts,
  upcomingEvents,
  unreadNotifications,
  isLoading = false,
}: WelcomeBannerProps) {
  const greeting = getGreeting();
  const dateLabel = getDateLabel();

  if (isLoading) {
    return (
      <Box
        sx={{
          position: "relative",
          borderRadius: "xl",
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.surface",
          px: { xs: 3, md: 4 },
          py: { xs: 3, md: 3.5 },
        }}
      >
        <Skeleton width={140} height={14} rounded="md" />
        <Box sx={{ height: 8 }} />
        <Skeleton width={320} height={36} rounded="md" />
        <Box sx={{ height: 16 }} />
        <Box sx={{ display: "flex", gap: 1.5 }}>
          <Skeleton width={120} height={40} rounded="md" />
          <Skeleton width={140} height={40} rounded="md" />
          <Skeleton width={130} height={40} rounded="md" />
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        position: "relative",
        borderRadius: "xl",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.surface",
        px: { xs: 3, md: 4 },
        py: { xs: 3, md: 3.5 },
        overflow: "hidden",
        // Terracotta accent line on the left edge for editorial rhythm.
        "&::before": {
          content: '""',
          position: "absolute",
          inset: "0 auto 0 0",
          width: "3px",
          background:
            "linear-gradient(180deg, var(--nx-palette-primary-500), var(--nx-palette-primary-700))",
        },
      }}
    >
      <Typography
        level="body-xs"
        sx={{
          textTransform: "uppercase",
          letterSpacing: "0.14em",
          color: "text.tertiary",
          fontWeight: 600,
        }}
      >
        {dateLabel}
      </Typography>

      <Typography
        level="h2"
        sx={{
          mt: 0.5,
          fontFamily: "var(--font-display)",
          fontWeight: 500,
          letterSpacing: "-0.01em",
          color: "text.primary",
        }}
      >
        {greeting}, {userName}.
      </Typography>

      <Box
        sx={{ mt: 2.5, display: "flex", flexWrap: "wrap", gap: 1.25 }}
        role="list"
        aria-label="Activity summary"
      >
        <div role="listitem">
          <StatChip
            count={newPosts}
            label="new posts"
            href="/app#feed"
            ariaLabel={`${newPosts} new posts since your last visit`}
          />
        </div>
        <div role="listitem">
          <StatChip
            count={upcomingEvents}
            label="upcoming events"
            href="/app/events"
            ariaLabel={`${upcomingEvents} upcoming events in the next 7 days`}
          />
        </div>
        <div role="listitem">
          <StatChip
            count={unreadNotifications}
            label="notifications"
            href="/app#activity"
            ariaLabel={`${unreadNotifications} unread notifications`}
          />
        </div>
      </Box>
    </Box>
  );
}

export default WelcomeBanner;
