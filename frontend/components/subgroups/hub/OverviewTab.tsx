"use client";
/**
 * @file components/subgroups/hub/OverviewTab.tsx
 * @brief Overview tab: pinned post, upcoming events, recent posts.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { EmptyState } from "@/components/ui";
import { EventCard } from "@/components/events/EventCard";
import { PostCard } from "@/components/feed/PostCard";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { useFeed } from "@/hooks/usePosts";
import { usePost } from "@/hooks/usePosts";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface OverviewTabProps {
  subgroup: SubgroupDetail;
}

export function OverviewTab({ subgroup }: OverviewTabProps) {
  const pinnedPost = usePost(subgroup.pinned_post_id ?? undefined);
  const upcomingEventsQuery = useUpcomingEvents(30, subgroup.id);
  const feedQuery = useFeed({ subgroup_id: subgroup.id }, 3);

  const upcomingEvents = upcomingEventsQuery.data?.items ?? [];
  const feedPages = feedQuery.data?.pages ?? [];
  const recentPosts = feedPages.flatMap((p) => p.items);

  return (
    <Stack spacing={3}>
      {/* Pinned Post Block */}
      {subgroup.pinned_post_id && pinnedPost.data ? (
        <Stack spacing={1}>
          <Typography level="title-sm">Pinned Post</Typography>
          <PostCard post={pinnedPost.data} truncateBody />
        </Stack>
      ) : null}

      {/* Upcoming Events Rail */}
      <Stack spacing={1}>
        <Typography level="title-sm">Upcoming Events</Typography>
        {upcomingEventsQuery.isLoading ? (
          <Typography level="body-sm">Loading...</Typography>
        ) : upcomingEvents.length === 0 ? (
          <EmptyState
            title="No upcoming events"
            description="Check back soon!"
          />
        ) : (
          <Stack spacing={2}>
            {upcomingEvents.slice(0, 5).map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </Stack>
        )}
      </Stack>

      {/* Recent Posts Preview */}
      <Stack spacing={1}>
        <Typography level="title-sm">Recent Posts</Typography>
        {feedQuery.isLoading ? (
          <Typography level="body-sm">Loading...</Typography>
        ) : recentPosts.length === 0 ? (
          <EmptyState
            title="Quiet here"
            description="Be the first to share something with your community."
          />
        ) : (
          <Stack spacing={2}>
            {recentPosts.slice(0, 3).map((post) => (
              <PostCard key={post.id} post={post} truncateBody />
            ))}
          </Stack>
        )}
      </Stack>
    </Stack>
  );
}

export default OverviewTab;
