/**
 * @file components/layout/navItems.tsx
 * @brief Single source of truth for sidebar + mobile nav targets. Keeping
 *        them aligned avoids the bottom-nav-vs-rail drift the legacy app had.
 */
import type { ComponentType, SVGProps } from "react";
import {
  NewspaperIcon,
  ChatBubbleLeftRightIcon,
  CalendarDaysIcon,
  UserGroupIcon,
  PhotoIcon,
  FilmIcon,
  UsersIcon,
  Cog6ToothIcon,
} from "@heroicons/react/24/outline";

export type IconType = ComponentType<SVGProps<SVGSVGElement>>;

export interface NavItem {
  label: string;
  href: string;
  Icon: IconType;
  mobile?: boolean;
}

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/app") return pathname === "/app";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Home", href: "/app", Icon: NewspaperIcon, mobile: true },
  {
    label: "Chat",
    href: "/app/chat",
    Icon: ChatBubbleLeftRightIcon,
    mobile: true,
  },
  {
    label: "Events",
    href: "/app/events",
    Icon: CalendarDaysIcon,
    mobile: true,
  },
  { label: "Groups", href: "/app/subgroups", Icon: UserGroupIcon },
  { label: "Galleries", href: "/app/galleries", Icon: PhotoIcon },
  { label: "Media", href: "/app/media", Icon: FilmIcon },
  { label: "Members", href: "/app/members", Icon: UsersIcon },
  { label: "Admin", href: "/app/admin", Icon: Cog6ToothIcon },
];
