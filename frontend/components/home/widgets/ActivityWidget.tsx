"use client";
/**
 * @file components/home/widgets/ActivityWidget.tsx
 * @brief Activity digest widget — groups last 24h notifications by type
 *        and shows a summary line. Expands to show individual items.
 */
import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import { listNotifications, type NotificationItem } from "@/lib/api/notifications";
import { EmptyState, Skeleton, Button } from "@/components/ui";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline";
import type { WidgetContext } from "@/lib/widgets/registry";

const LIST_KEY = ["notifications", "activity-digest"] as const;

const TYPE_LABELS: Record<string, string> = {
  reaction: "reaction",
  comment: "comment",
  event_rsvp: "RSVP",
  mention: "mention",
  post: "post",
  gallery_activity: "gallery update",
  prompt: "prompt",
  prompt_summary: "prompt summary",
};

function labelFor(type: string): string {
  return TYPE_LABELS[type] ?? type.replace(/_/g, " ");
}

function summarise(items: NotificationItem[]): string {
  const counts: Record<string, number> = {};
  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  for (const n of items) {
    if (new Date(n.created_at).getTime() < cutoff) continue;
    counts[n.type] = (counts[n.type] ?? 0) + 1;
  }
  const parts = Object.entries(counts).map(
    ([type, count]) => `${count} ${labelFor(type)}${count !== 1 ? "s" : ""}`,
  );
  return parts.length > 0 ? parts.join(", ") : "";
}

function formatTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function ActivityWidget(_ctx: WidgetContext) {
  const [expanded, setExpanded] = React.useState(false);

  const { data, isLoading } = useQuery({
    queryKey: LIST_KEY,
    queryFn: () => listNotifications(undefined, 30),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Stack spacing={1}>
        <Skeleton height={24} width={200} rounded="md" />
        <Skeleton height={16} width={160} rounded="md" />
      </Stack>
    );
  }

  const items = data?.items ?? [];
  const summary = summarise(items);

  if (!summary) {
    return (
      <EmptyState
        title="No recent activity"
        description="Your last 24h activity will appear here."
      />
    );
  }

  const recent = items.slice(0, 5);

  return (
    <Stack spacing={1.5}>
      {/* Summary line */}
      <Typography level="body-sm" textColor="text.secondary">
        {summary}
      </Typography>

      {/* Expand toggle */}
      <Button
        variant="plain"
        size="sm"
        onClick={() => setExpanded((v) => !v)}
        startDecorator={
          expanded ? (
            <ChevronUpIcon width={14} />
          ) : (
            <ChevronDownIcon width={14} />
          )
        }
        sx={{ alignSelf: "flex-start" }}
      >
        {expanded ? "Collapse" : "Show recent"}
      </Button>

      {/* Item list */}
      {expanded && (
        <Stack spacing={0.5}>
          {recent.map((n) => {
            const message =
              typeof n.payload?.message === "string" ? n.payload.message : labelFor(n.type);
            const link =
              typeof n.payload?.link === "string" ? n.payload.link : null;

            const Row = (
              <Box
                sx={{
                  px: 1.5,
                  py: 1,
                  borderRadius: "sm",
                  background: !n.read_at ? "primary.softBg" : "transparent",
                  "&:hover": { background: "neutral.softBg" },
                }}
              >
                <Typography level="body-xs" textColor="text.tertiary">
                  {formatTime(n.created_at)}
                </Typography>
                <Typography level="body-sm" noWrap>
                  {message}
                </Typography>
              </Box>
            );

            if (link) {
              return (
                <Link
                  key={n.id}
                  href={link}
                  style={{ display: "block", color: "inherit", textDecoration: "none" }}
                >
                  {Row}
                </Link>
              );
            }
            return <div key={n.id}>{Row}</div>;
          })}
        </Stack>
      )}
    </Stack>
  );
}

export default ActivityWidget;
