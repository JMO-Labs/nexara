/**
 * @file lib/occasions.tsx
 * @brief Wishlist occasions: label, icon, accent and whether gifts should be
 *        a surprise by default (gift occasions) or open (gatherings).
 */
import {
  Baby,
  Backpack,
  Cake,
  Gem,
  Gift,
  GraduationCap,
  HeartHandshake,
  HeartPulse,
  House,
  PartyPopper,
  Plane,
  Snowflake,
  Sparkles,
  Sunset,
  Users,
  type LucideIcon,
} from "lucide-react";

export type Occasion =
  | "birthday"
  | "baby_shower"
  | "wedding"
  | "bridal_shower"
  | "anniversary"
  | "graduation"
  | "retirement"
  | "housewarming"
  | "holiday"
  | "back_to_school"
  | "reunion"
  | "party"
  | "get_well"
  | "farewell"
  | "custom";

export interface OccasionMeta {
  label: string;
  Icon: LucideIcon;
  /** CSS color for the icon disc (palette tokens or door colors). */
  tint: string;
  /** Gifts are a surprise by default (hide claims from the people it's for). */
  surprise: boolean;
}

export const OCCASIONS: Record<Occasion, OccasionMeta> = {
  birthday: {
    label: "Birthday",
    Icon: Cake,
    tint: "var(--nx-red)",
    surprise: true,
  },
  baby_shower: {
    label: "Baby shower",
    Icon: Baby,
    tint: "#5C8FA8",
    surprise: true,
  },
  wedding: {
    label: "Wedding",
    Icon: HeartHandshake,
    tint: "#A8505F",
    surprise: true,
  },
  bridal_shower: {
    label: "Bridal shower",
    Icon: Gem,
    tint: "#7D5A7A",
    surprise: true,
  },
  anniversary: {
    label: "Anniversary",
    Icon: Sparkles,
    tint: "#C9973F",
    surprise: true,
  },
  graduation: {
    label: "Graduation",
    Icon: GraduationCap,
    tint: "#2F5873",
    surprise: true,
  },
  retirement: {
    label: "Retirement",
    Icon: Sunset,
    tint: "#C9973F",
    surprise: true,
  },
  housewarming: {
    label: "Housewarming",
    Icon: House,
    tint: "#7A8A55",
    surprise: true,
  },
  holiday: {
    label: "Holiday",
    Icon: Snowflake,
    tint: "#5C8FA8",
    surprise: true,
  },
  back_to_school: {
    label: "Back to school",
    Icon: Backpack,
    tint: "#2F5873",
    surprise: false,
  },
  reunion: {
    label: "Family reunion",
    Icon: Users,
    tint: "#7A8A55",
    surprise: false,
  },
  party: {
    label: "Party or BBQ",
    Icon: PartyPopper,
    tint: "#C9973F",
    surprise: false,
  },
  get_well: {
    label: "Get well",
    Icon: HeartPulse,
    tint: "#A8505F",
    surprise: true,
  },
  farewell: { label: "Farewell", Icon: Plane, tint: "#5C8FA8", surprise: true },
  custom: {
    label: "Something else",
    Icon: Gift,
    tint: "var(--nx-accent)",
    surprise: true,
  },
};

/** @brief The list's occasion name: the free-form label wins over the preset. */
export const occasionName = (o: Occasion, label?: string | null) =>
  label?.trim() || OCCASIONS[o].label;
