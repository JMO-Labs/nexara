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
    <Stack spacing={1.25}>
      <Typography
        level="body-sm"
        sx={{ color: "text.primary", lineHeight: 1.5 }}
      >
        {summary}
      </Typography>

      <Button
        variant="plain"
        size="sm"
        color="neutral"
        onClick={() => setExpanded((v) => !v)}
        startDecorator={
          expanded ? <ChevronUpIcon width={12} /> : <ChevronDownIcon width={12} />
        }
        sx={{
          alignSelf: "flex-start",
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          color: "text.tertiary",
          minHeight: 0,
          py: 0.25,
          px: 0.75,
          "&:hover": { color: "text.primary", bgcolor: "transparent" },
        }}
      >
        {expanded ? "Hide" : "Recent"}
      </Button>

      {expanded && (
        <Stack
          spacing={0}
          sx={{ borderTop: "1px solid", borderColor: "divider" }}
        >
          {recent.map((n) => {
            const message =
              typeof n.payload?.message === "string"
                ? n.payload.message
                : labelFor(n.type);
            const link =
              typeof n.payload?.link === "string" ? n.payload.link : null;

            const Row = (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 1.25,
                  py: 1,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  position: "relative",
                  transition: "background-color 120ms",
                  "&:hover": { bgcolor: "background.level1" },
                  ...(n.read_at
                    ? {}
                    : {
                        "&::before": {
                          content: '""',
                          position: "absolute",
                          left: -8,
                          top: "calc(50% - 3px)",
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          bgcolor: "primary.500",
                        },
                      }),
                }}
              >
                <Typography
                  level="body-xs"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: "text.tertiary",
                    flexShrink: 0,
                    width: 64,
                  }}
                >
                  {formatTime(n.created_at)}
                </Typography>
                <Typography
                  level="body-sm"
                  sx={{
                    color: "text.primary",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    minWidth: 0,
                    flex: 1,
                  }}
                >
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
