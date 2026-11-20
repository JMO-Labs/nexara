"use client";
/**
 * @file components/subgroups/hub/OverviewTab.tsx
 * @brief Overview tab: pinned post, upcoming events, recent posts.
 */
import * as React from "react";
import { CalendarDays, Newspaper, Pin } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { Panel } from "@/components/ui/page";
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
    <div className="flex flex-col gap-4 md:gap-[18px]">
      {subgroup.pinned_post_id && pinnedPost.data ? (
        <Panel
          as="section"
          aria-label="Pinned post"
          title="Pinned post"
          icon={Pin}
        >
          <PostCard post={pinnedPost.data} truncateBody />
        </Panel>
      ) : null}

      <Panel
        as="section"
        aria-label="Upcoming events"
        title="Upcoming events"
        icon={CalendarDays}
      >
        {upcomingEventsQuery.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : upcomingEvents.length === 0 ? (
          <EmptyState
            compact
            icon={CalendarDays}
            title="No upcoming events"
            description="Check back soon."
          />
        ) : (
          <div className="flex flex-col gap-4">
            {upcomingEvents.slice(0, 5).map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        )}
      </Panel>

      <Panel
        as="section"
        aria-label="Recent posts"
        title="Recent posts"
        icon={Newspaper}
      >
        {feedQuery.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : recentPosts.length === 0 ? (
          <EmptyState
            compact
            icon={Newspaper}
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
      </Panel>
    </div>
  );
}

export default OverviewTab;
