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
  Film,
  Contact,
  Trophy,
  Bell,
  Settings,
  ShieldCheck,
  CircleHelp,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
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

export const PRIMARY_NAV: NavItem[] = [
  { label: "Home", href: "/app", Icon: House },
  { label: "Chat", href: "/app/chat", Icon: MessageCircle },
  { label: "Calendar", href: "/app/events", Icon: CalendarDays },
  { label: "Groups", href: "/app/subgroups", Icon: Users },
];

export const MORE_NAV: NavItem[] = [
  { label: "Galleries", href: "/app/galleries", Icon: Images },
  { label: "Media", href: "/app/media", Icon: Film },
  { label: "Kudos", href: "/app/kudos", Icon: Trophy },
  { label: "Members", href: "/app/members", Icon: Contact },
  { label: "Notifications", href: "/app/notifications", Icon: Bell },
  { label: "Settings", href: "/app/settings", Icon: Settings },
  { label: "Admin", href: "/app/admin", Icon: ShieldCheck, adminOnly: true },
  { label: "Help", href: "/app/help", Icon: CircleHelp },
];
