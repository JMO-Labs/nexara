/**
 * @file components/home/widgetRegistry.tsx
 * @brief Static list of home sidebar widgets, in default order.
 */
import type { ComponentType } from "react";
import { UpcomingEventsWidget } from "./widgets/UpcomingEventsWidget";
import { NextEventCountdownWidget } from "./widgets/NextEventCountdownWidget";
import { MyGroupsWidget } from "./widgets/MyGroupsWidget";
import { MediaCarouselWidget } from "./widgets/MediaCarouselWidget";
import { QuickActionsWidget } from "./widgets/QuickActionsWidget";

export type WidgetId =
  | "upcoming-events"
  | "my-groups"
  | "media"
  | "quick-actions"
  | "next-event-countdown";

export const WIDGETS: {
  id: WidgetId;
  title: string;
  Component: ComponentType;
}[] = [
  {
    id: "upcoming-events",
    title: "Upcoming events",
    Component: UpcomingEventsWidget,
  },
  { id: "my-groups", title: "My groups", Component: MyGroupsWidget },
  { id: "media", title: "Media", Component: MediaCarouselWidget },
  {
    id: "quick-actions",
    title: "Quick actions",
    Component: QuickActionsWidget,
  },
  {
    id: "next-event-countdown",
    title: "Next event",
    Component: NextEventCountdownWidget,
  },
];
