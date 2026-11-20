/**
 * @file components/layout/navItems.tsx
 * @brief Single source of truth for side nav, bottom tab bar and More sheet.
 */
import {
  House,
  MessageCircle,
  CalendarDays,
  Users,
  Images,
  List,
  Contact,
  Trophy,
  Bell,
  Bookmark,
  Settings,
  ShieldCheck,
  CircleHelp,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  /** Absent for action items (no route). */
  href?: string;
  /** Non-link behaviour; "help" opens the shortcuts/help surface. */
  action?: "help";
  Icon: LucideIcon;
  adminOnly?: boolean;
}

/**
 * @brief Whether a nav href is active for the pathname.
 * @param pathname current path
 * @param href nav target
 * @return true when active
 */
export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/app") return pathname === "/app";
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * @brief Filter out admin-only items for non-admins.
 * @param items nav items
 * @param isAdmin viewer is admin
 * @return visible items
 */
/**
 * @brief Admin check. Backend exposes only `role`, never `is_admin`.
 * @param user session user or null
 * @return true when role is admin
 */
export function isAdmin(user?: { role?: string } | null): boolean {
  return user?.role === "admin";
}

export function visibleNav(items: NavItem[], isAdmin: boolean): NavItem[] {
  return items.filter((i) => !i.adminOnly || isAdmin);
}

/** @brief Phone tab bar items (Create sits between the halves). */
export const TAB_NAV: NavItem[] = [
  { label: "Home", href: "/app", Icon: House },
  { label: "Chat", href: "/app/chat", Icon: MessageCircle },
  { label: "Calendar", href: "/app/events", Icon: CalendarDays },
  { label: "Photos", href: "/app/photos", Icon: Images },
];

/** @brief Desktop top pill nav; overflow lives under a More dropdown. */
export const TOP_NAV: NavItem[] = [
  ...TAB_NAV,
  { label: "Groups", href: "/app/subgroups", Icon: Users },
];

/** @brief Top-nav items that the phone tab bar has no room for (shown first in the More sheet). */
export const PHONE_EXTRA_NAV: NavItem[] = TOP_NAV.filter(
  (t) => !TAB_NAV.some((x) => x.href === t.href),
);

export const MORE_NAV: NavItem[] = [
  { label: "People", href: "/app/members", Icon: Contact },
  { label: "Lists", href: "/app/lists", Icon: List },
  { label: "Kudos", href: "/app/kudos", Icon: Trophy },
  { label: "Saved", href: "/app/bookmarks", Icon: Bookmark },
  { label: "Notifications", href: "/app/notifications", Icon: Bell },
  { label: "Settings", href: "/app/settings", Icon: Settings },
  { label: "Admin", href: "/app/admin", Icon: ShieldCheck, adminOnly: true },
  { label: "Help", action: "help", Icon: CircleHelp },
];
