/**
 * @file components/subgroups/hub/tabs.ts
 * @brief Group hub tab registry + metadata.
 */
import type { LucideIcon } from "lucide-react";
import type { SubgroupDetail } from "@/lib/api/subgroups";
import {
  Home,
  CalendarDays,
  Image as ImageIcon,
  Newspaper,
  List,
  Users,
  Settings,
} from "lucide-react";
import { OverviewTab } from "./OverviewTab";
import { EventsTab } from "./EventsTab";
import { PhotosTab } from "./PhotosTab";
import { PostsTab } from "./PostsTab";
import { ListsTab } from "./ListsTab";
import { MembersTab } from "./MembersTab";
import { SettingsTab } from "./SettingsTab";

export type IconType = LucideIcon;

export interface GroupTab {
  id: string;
  label: string;
  Icon: IconType;
  Component?: React.ComponentType<{ subgroup: SubgroupDetail }>;
  visible?: (s: SubgroupDetail) => boolean;
}

export const GROUP_TABS: GroupTab[] = [
  { id: "overview", label: "Overview", Icon: Home, Component: OverviewTab },
  {
    id: "events",
    label: "Events",
    Icon: CalendarDays,
    Component: EventsTab,
  },
  { id: "photos", label: "Photos", Icon: ImageIcon, Component: PhotosTab },
  { id: "posts", label: "Posts", Icon: Newspaper, Component: PostsTab },
  { id: "lists", label: "Lists", Icon: List, Component: ListsTab },
  { id: "members", label: "Members", Icon: Users, Component: MembersTab },
  {
    id: "settings",
    label: "Settings",
    Icon: Settings,
    Component: SettingsTab,
    visible: (s) => s.my_role === "owner" || s.my_role === "moderator",
  },
];

/**
 * Tabs accessible to non-members of invite_only/admin_approval groups.
 */
export function getVisibleTabs(subgroup: SubgroupDetail): GroupTab[] {
  const isMember = !!subgroup.my_role;
  const isOpen = subgroup.join_policy === "open";

  if (isMember || isOpen) {
    return GROUP_TABS.filter((tab) => !tab.visible || tab.visible(subgroup));
  }

  // Non-members of restricted groups only see the gate
  return [];
}
