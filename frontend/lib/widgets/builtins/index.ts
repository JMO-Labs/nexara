/**
 * @file lib/widgets/builtins/index.ts
 * @brief Side-effect barrel that registers all built-in widgets.
 *        Import this file once (e.g. in app root page) to register
 *        all core widgets before first render.
 */
import { register } from "@/lib/widgets/registry";

// Lazy-import component refs to keep bundle splits intact.
// These are imported synchronously here because registration is
// a side-effect that must complete before the registry is read.
import { FeedWidget } from "@/components/home/widgets/FeedWidget";
import { UpcomingEventsWidget } from "@/components/home/widgets/UpcomingEventsWidget";
import { MediaCarouselWidget } from "@/components/home/widgets/MediaCarouselWidget";
import { ActivityWidget } from "@/components/home/widgets/ActivityWidget";
import { QuickActionsWidget } from "@/components/home/widgets/QuickActionsWidget";
import { MyGroupsWidget } from "@/components/home/widgets/MyGroupsWidget";

register({
  id: "feed",
  title: "Community Feed",
  description: "Posts from your community and all groups you belong to.",
  defaultSize: "lg",
  category: "core",
  Component: FeedWidget,
});

register({
  id: "upcoming-events",
  title: "Upcoming Events",
  description: "Events in your community and groups over the next 7–30 days.",
  defaultSize: "md",
  category: "core",
  Component: UpcomingEventsWidget,
});

register({
  id: "media-carousel",
  title: "Media Carousel",
  description: "Recent photos and videos from across your groups.",
  defaultSize: "full",
  category: "media",
  Component: MediaCarouselWidget,
});

register({
  id: "activity",
  title: "Activity Digest",
  description: "Your last 24h notifications grouped by type.",
  defaultSize: "sm",
  category: "social",
  Component: ActivityWidget,
});

register({
  id: "quick-actions",
  title: "Quick Actions",
  description: "Shortcuts to create a post, event, or upload media.",
  defaultSize: "sm",
  category: "core",
  Component: QuickActionsWidget,
});

register({
  id: "my-groups",
  title: "My Groups",
  description: "Compact view of the groups you belong to.",
  defaultSize: "sm",
  category: "social",
  Component: MyGroupsWidget,
});

export {};
