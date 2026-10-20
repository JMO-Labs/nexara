"use client";
/**
 * @file components/home/widgets/ActivityWidget.tsx
 * @brief Activity feed widget — displays aggregated community activities.
 *        Groups posts, media uploads, RSVPs, comments, etc. by actor/target.
 */
import * as React from "react";
import Link from "next/link";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import { useActivityFeed, type ActivityItem } from "@/hooks/useActivityFeed";
import { EmptyState, Skeleton, Button } from "@/components/ui";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline";
import type { WidgetContext } from "@/lib/widgets/registry";

/**
 * @brief Format activity item into human-readable text.
 *
 * Maps verb + object_type to a template, substituting actor/container/object names.
 * Examples:
 *   "Sue posted in Family"
 *   "John added 4 photos to Trip Album"
 */
function formatActivity(item: ActivityItem): string {
  const {
    actor_name,
    verb,
    object_type,
    object_title,
    container_title,
    count,
  } = item;

  // Verb templates: verb -> (template_with_placeholders, use_count)
  const templates: Record<string, [string, boolean]> = {
    "post.created": ["{actor} posted", false],
    "post.commented": ["{actor} commented on a post", false],
    "post.reacted": ["{actor} reacted", false],
    "event.created": ["{actor} created {object}", false],
    "event.rsvp": ["{actor} RSVP'd", false],
    "gallery.created": ["{actor} created gallery {object}", false],
    "media.uploaded": [
      "{actor} added {count} {obj_plural} to {container}",
      true,
    ],
    "chat.posted": ["{actor} posted in {container}", false],
    "member.joined": ["{actor} joined", false],
    "subgroup.created": ["{actor} created subgroup {object}", false],
    "prompt.responded": ["{actor} responded to {object}", false],
  };

  const [template, useCount] = templates[verb] ?? ["{actor} {verb}", false];

  let text = template
    .replace("{actor}", actor_name)
    .replace("{object}", object_title || "it")
    .replace("{container}", container_title || "community")
    .replace("{verb}", verb);

  if (useCount && count > 1) {
    text = text.replace("{count}", String(count));
    // Pluralize "photo" -> "photos"
    if (object_title) {
      const singular = object_type === "media" ? "photo" : object_type;
      text = text.replace("{obj_plural}", `${singular}s`);
    }
  } else {
    text = text.replace("{count}", "1");
  }

  return text;
}

/**
 * @brief Resolve the click-through link for an activity item.
 *
 * Maps object_type + object_id to a route.
 */
function resolveObjectRoute(objectType: string, objectId: string): string {
  switch (objectType) {
    case "post":
      return `/app/posts/${objectId}`;
    case "event":
      return `/app/events/${objectId}`;
    case "gallery":
      return `/app/galleries/${objectId}`;
    case "media":
      // Media typically links to the source (post/gallery/event)
      return `/app/galleries/${objectId}`;
    case "comment":
      // Links to the commented-on post (object_id is actually the post id in metadata)
      return `/app/posts/${objectId}`;
    case "subgroup":
      return `/app/subgroups/${objectId}`;
    default:
      return `/app`;
  }
}

export function ActivityWidget(_ctx: WidgetContext) {
  const [expanded, setExpanded] = React.useState(false);

  const { data, isLoading, isError, hasNextPage, fetchNextPage } =
    useActivityFeed({
      limit: 10,
    });

  if (isLoading) {
    return (
      <Stack spacing={1}>
        <Skeleton height={24} width={200} rounded="md" />
        <Skeleton height={16} width={160} rounded="md" />
      </Stack>
    );
  }

  if (isError) {
    return (
      <EmptyState
        title="Activity unavailable"
        description="Couldn't load activity feed. Try again later."
      />
    );
  }

  // Flatten paginated results (usually just the first page)
  const items = data?.pages.flatMap((page) => page.items).slice(0, 5) ?? [];

  function formatTime(iso: string): string {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86_400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(iso).toLocaleDateString();
  }

  if (items.length === 0) {
    return (
      <EmptyState
        title="No recent activity"
        description="Community activity will appear here."
      />
    );
  }

  const showItems = expanded || items.length > 0;

  return (
    <Stack spacing={1.25}>
      {items.length > 0 && (
        <>
          <Typography
            level="body-sm"
            sx={{ color: "text.primary", lineHeight: 1.5 }}
          >
            Recent activity
          </Typography>

          {items.length > 1 && (
            <Button
              variant="plain"
              size="sm"
              color="neutral"
              onClick={() => setExpanded((v) => !v)}
              startDecorator={
                expanded ? (
                  <ChevronUpIcon width={12} />
                ) : (
                  <ChevronDownIcon width={12} />
                )
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
              {expanded ? "Hide" : "Details"}
            </Button>
          )}
        </>
      )}

      {showItems && (
        <Stack
          spacing={0}
          sx={{ borderTop: "1px solid", borderColor: "divider" }}
        >
          {items.map((item) => {
            const message = formatActivity(item);
            const link = resolveObjectRoute(item.object_type, item.object_id);

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
                  {formatTime(item.created_at)}
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

            return (
              <Link
                key={item.id}
                href={link}
                style={{
                  display: "block",
                  color: "inherit",
                  textDecoration: "none",
                }}
              >
                {Row}
              </Link>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}

export default ActivityWidget;
