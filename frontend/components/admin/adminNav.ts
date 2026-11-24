/**
 * @file components/admin/adminNav.ts
 * @brief Admin section registry: grouped nav items and active-id resolution.
 */
import {
  BarChart3,
  BellRing,
  Bot,
  Brush,
  Database,
  Hash,
  ToggleRight,
  History,
  KeyRound,
  Mail,
  MailPlus,
  MessageSquareQuote,
  Puzzle,
  Send,
  Settings,
  ShieldAlert,
  ShoppingBag,
  Timer,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface AdminItem {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

export interface AdminGroup {
  label: string;
  items: AdminItem[];
}

const BASE = "/app/admin";
/** @brief Tab item served by the /app/admin index route. */
const tab = (
  id: string,
  label: string,
  description: string,
  icon: LucideIcon,
): AdminItem => ({ id, label, description, icon, href: `${BASE}?tab=${id}` });
/** @brief Item served by its own sub-route. */
const route = (
  id: string,
  label: string,
  description: string,
  icon: LucideIcon,
): AdminItem => ({ id, label, description, icon, href: `${BASE}/${id}` });

/** @brief Grouped admin sections (15 tabs + 4 route links). */
export const ADMIN_GROUPS: AdminGroup[] = [
  {
    label: "Community",
    items: [
      tab("metrics", "Metrics", "Community and system at a glance.", BarChart3),
      tab(
        "branding",
        "Branding",
        "Name, colours, fonts and custom CSS.",
        Brush,
      ),
    ],
  },
  {
    label: "People",
    items: [
      tab("users", "Users", "View and manage members and their roles.", Users),
      tab(
        "invites",
        "Invites",
        "Invite new members to the community.",
        MailPlus,
      ),
      tab("sso", "SSO", "Single sign-on providers.", KeyRound),
    ],
  },
  {
    label: "Content",
    items: [
      tab(
        "interests",
        "Interests",
        "Interest categories members can pick.",
        Hash,
      ),
      tab(
        "prompts",
        "Prompts",
        "Community prompts and schedules.",
        MessageSquareQuote,
      ),
      tab(
        "features",
        "Features",
        "Turn community features on or off.",
        ToggleRight,
      ),
      route(
        "moderation",
        "Moderation",
        "Review reported content.",
        ShieldAlert,
      ),
      route(
        "retention",
        "Retention",
        "Control how long each type of content is kept.",
        Timer,
      ),
    ],
  },
  {
    label: "System",
    items: [
      route(
        "storage",
        "Storage",
        "Usage trends and per-user breakdown.",
        Database,
      ),
      tab("ai", "AI", "AI providers and usage.", Bot),
      tab(
        "shopping",
        "Shopping",
        "Amazon keys for live wishlist prices.",
        ShoppingBag,
      ),
      tab(
        "email",
        "Email",
        "Outgoing mail server (SMTP) for invites and notifications.",
        Send,
      ),
      tab(
        "alerts",
        "Alerts",
        "Where admin alerts are sent (ntfy, Discord and more).",
        BellRing,
      ),
      tab(
        "email-reply",
        "Email replies",
        "Let members reply to emails to comment.",
        Mail,
      ),
      route(
        "plugins",
        "Plugins",
        "Install, configure and manage plugins.",
        Puzzle,
      ),
      tab("audit-log", "Audit log", "Who did what, and when.", History),
      tab("settings", "Settings", "Community-wide settings.", Settings),
    ],
  },
];

/** @brief Flat list of every admin item. */
export const ADMIN_ITEMS: AdminItem[] = ADMIN_GROUPS.flatMap((g) => g.items);

/**
 * @brief Resolve the active nav id.
 * @param pathname current pathname
 * @param tabParam value of ?tab= (index route only)
 * @return item id
 */
export function adminActiveId(
  pathname: string,
  tabParam: string | null,
): string {
  const rest = pathname.replace(/^\/app\/admin\/?/, "").split("/")[0];
  return rest || tabParam || "metrics";
}
