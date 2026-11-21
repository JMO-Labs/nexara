"use client";
/**
 * @file components/home/NeedsChips.tsx
 * @brief "Needs you" glass pill with action chips (RSVPs, polls, prompt, lists).
 */
import Link from "next/link";
import {
  BarChart3,
  CalendarCheck,
  Inbox,
  ListChecks,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useHomeNeeds } from "@/hooks/useHomeNeeds";

interface Chip {
  key: string;
  text: string;
  href: string;
  icon: LucideIcon;
  hot?: boolean;
}

/**
 * @brief Truncate to 28 chars with an ellipsis.
 * @param s Text.
 * @return Possibly truncated text.
 */
function clip(s: string): string {
  return s.length > 28 ? `${s.slice(0, 28)}…` : s;
}

/**
 * @brief Needs-you chips; renders nothing when there is nothing to do.
 * @return Glass pill, or null.
 */
export function NeedsChips() {
  const { data } = useHomeNeeds();
  if (!data) return null;

  const chips: Chip[] = [
    ...data.rsvps.map((r) => ({
      key: `r-${r.event_id}`,
      text: `RSVP to ${r.title}`,
      href: `/app/events?event=${r.event_id}`,
      icon: CalendarCheck,
      hot: true,
    })),
    ...data.polls.map((p) => ({
      key: `p-${p.post_id}`,
      text: `Vote: ${p.question}`,
      href: `/app/post/${p.post_id}`,
      icon: BarChart3,
    })),
    ...(data.prompt
      ? [
          {
            key: "prompt",
            text: "Today's prompt",
            href: `/app/prompts/${data.prompt.prompt_post_id}`,
            icon: Sparkles,
          },
        ]
      : []),
    ...(data.list_items
      ? [
          {
            key: "lists",
            text: `${data.list_items.count} list items due`,
            href: `/app/lists/${data.list_items.list_id}`,
            icon: ListChecks,
            hot: true,
          },
        ]
      : []),
  ];
  if (chips.length === 0) return null;

  return (
    <div
      aria-label="Needs you"
      className="glass flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto rounded-[22px] py-1 pr-1 pl-3 md:rounded-full md:pl-4"
    >
      <span className="mr-1.5 inline-flex shrink-0 items-center gap-1.5 text-[13px] whitespace-nowrap text-[var(--nx-muted)]">
        <Inbox aria-hidden className="size-[15px]" />
        Needs you
      </span>
      {chips.map(({ key, text, href, icon: Icon, hot }) => (
        <Link
          key={key}
          href={href}
          aria-label={text}
          className="glass-item inline-flex h-[34px] shrink-0 items-center gap-[7px] rounded-full px-3.5 text-[13.5px] whitespace-nowrap"
        >
          <Icon
            aria-hidden
            className={`size-[15px] ${hot ? "text-[var(--nx-red)]" : ""}`}
          />
          {clip(text)}
        </Link>
      ))}
    </div>
  );
}
