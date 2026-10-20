"use client";
/**
 * @file components/subgroups/hub/OverviewTab.tsx
 * @brief Overview tab: pinned post, upcoming events, recent posts.
 */
import * as React from "react";
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
    <div className="flex flex-col gap-6">
      {/* Pinned post Block */}
      {subgroup.pinned_post_id && pinnedPost.data ? (
        <div className="flex flex-col gap-2">
          <h3 className="text-base font-semibold">Pinned post</h3>
          <PostCard post={pinnedPost.data} truncateBody />
        </div>
      ) : null}

      {/* Upcoming events Rail */}
      <div className="flex flex-col gap-2">
        <h3 className="text-base font-semibold">Upcoming events</h3>
        {upcomingEventsQuery.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : upcomingEvents.length === 0 ? (
          <EmptyState
            title="No upcoming events"
            description="Check back soon!"
          />
        ) : (
          <div className="flex flex-col gap-4">
            {upcomingEvents.slice(0, 5).map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>

      {/* Recent posts Preview */}
      <div className="flex flex-col gap-2">
        <h3 className="text-base font-semibold">Recent posts</h3>
        {feedQuery.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : recentPosts.length === 0 ? (
          <EmptyState
            title="Quiet here"
            description="Be the first to share something with your community."
          />
        ) : (
          <div className="flex flex-col gap-4">
            {recentPosts.slice(0, 3).map((post) => (
              <PostCard key={post.id} post={post} truncateBody />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default OverviewTab;
