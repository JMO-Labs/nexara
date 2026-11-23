/**
 * @file components/layout/navItems.tsx
 * @brief Single source of truth for side nav, bottom tab bar and More sheet.
 */
import {
  CalendarDays,
  ChefHat,
  Gift,
  Hourglass,
  House,
  Images,
  Inbox,
  MessageCircle,
  Network,
  Newspaper,
  Receipt,
  Settings,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  /** Extra path prefixes that also mark this item active. */
  match?: string[];
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
 * @brief Whether a nav item is active: its href or any match prefix.
 * @param pathname current path
 * @param item nav item
 * @return true when active
 */
export function isItemActive(pathname: string, item: NavItem): boolean {
  return [item.href, ...(item.match ?? [])].some((h) =>
    isNavActive(pathname, h),
  );
}

/**
 * @brief Admin check. Backend exposes only `role`, never `is_admin`.
 * @param user session user or null
 * @return true when role is admin
 */
export function isAdmin(user?: { role?: string } | null): boolean {
  return user?.role === "admin";
}

/**
 * @brief Filter out admin-only items for non-admins.
 * @param items nav items
 * @param isAdmin viewer is admin
 * @return visible items
 */
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

/** @brief Desktop top pill nav. Settings/Admin live in the avatar menu. */
export const TOP_NAV: NavItem[] = [
  ...TAB_NAV,
  {
    label: "Community",
    href: "/app/community",
    Icon: Users,
    match: ["/app/members", "/app/subgroups"],
  },
  {
    label: "Wishlists",
    href: "/app/wishlists",
    Icon: Gift,
  },
  { label: "Family", href: "/app/family", Icon: Network },
  {
    label: "Inbox",
    href: "/app/inbox",
    Icon: Inbox,
    match: ["/app/notifications", "/app/bookmarks", "/app/lists"],
  },
];

/** @brief Simple mode nav: Home feed, Photos, Family, Calendar (in order). */
export const SIMPLE_NAV_HREFS = [
  "/app",
  "/app/photos",
  "/app/family",
  "/app/events",
] as const;

/** @brief Simple mode nav items, in SIMPLE_NAV_HREFS order. */
export const SIMPLE_NAV: NavItem[] = SIMPLE_NAV_HREFS.map(
  (h) => TOP_NAV.find((t) => t.href === h) as NavItem,
);

/** @brief Top-nav items that the phone tab bar has no room for (shown first in the More sheet). */
export const PHONE_EXTRA_NAV: NavItem[] = TOP_NAV.filter(
  (t) => !TAB_NAV.some((x) => x.href === t.href),
);

/** @brief Phone More sheet extras (desktop uses the avatar menu). */
export const MORE_NAV: NavItem[] = [
  { label: "Time capsules", href: "/app/capsules", Icon: Hourglass },
  { label: "Recipes", href: "/app/recipes", Icon: ChefHat },
  { label: "Newsletter", href: "/app/newsletter", Icon: Newspaper },
  { label: "Shared costs", href: "/app/expenses", Icon: Receipt },
  { label: "Settings", href: "/app/settings", Icon: Settings },
  { label: "Admin", href: "/app/admin", Icon: ShieldCheck, adminOnly: true },
];
