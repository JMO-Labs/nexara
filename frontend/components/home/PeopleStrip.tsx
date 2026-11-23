"use client";
/**
 * @file components/home/PeopleStrip.tsx
 * @brief Glass pill of ringed avatars with online dot, birthday badge, hover card.
 *        Shows only pinned people once the viewer pins anyone (star on the
 *        hover card or profile); until then, a suggested ranking.
 */
import { Cake } from "lucide-react";
import { HoverCard } from "radix-ui";
import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { ConnectionCard } from "@/components/home/ConnectionCard";
import { useHomePeople } from "@/hooks/useHomePeople";
import type { HomePerson } from "@/lib/api/home";
import { groupColor } from "@/lib/groupColor";

/**
 * @brief Compact relative time such as "3h ago".
 * @param iso ISO timestamp.
 * @return Relative string.
 */
function relative(iso: string): string {
  const mins = Math.max(0, Math.floor((Date.now() - Date.parse(iso)) / 60_000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * @brief Status text for a person.
 * @param p Person.
 * @return Status, or "" when nothing is known.
 */
function statusOf(p: HomePerson): string {
  if (p.online) return "Online now";
  if (p.birthday_in_days === 0) return "Birthday today";
  if (p.birthday_in_days != null) {
    return `Birthday in ${p.birthday_in_days} days`;
  }
  if (p.last_seen_at) return `Active ${relative(p.last_seen_at)}`;
  return "";
}

/**
 * @brief People strip; renders nothing when there are no people.
 * @return Glass pill of people.
 */
export function PeopleStrip() {
  const router = useRouter();
  const { data } = useHomePeople();
  const all = data?.items ?? [];
  const pinned = all.filter((p) => p.favorite);
  const people = pinned.length ? pinned : all;
  if (people.length === 0) return null;

  return (
    <div
      aria-label={pinned.length ? "Pinned people" : "Your people"}
      className="glass flex gap-3 overflow-x-auto rounded-3xl p-2.5 md:gap-2 md:overflow-visible md:rounded-full md:px-2.5 md:py-2"
    >
      {people.map((p) => {
        const status = statusOf(p);
        const accent = p.shared_groups.find(
          (g) => g.id === p.primary_group_id,
        )?.accent_color;
        const ring = groupColor(p.primary_group_id, accent);
        return (
          <HoverCard.Root key={p.user_id} openDelay={120} closeDelay={250}>
            <HoverCard.Trigger asChild>
              <button
                type="button"
                aria-label={
                  status ? `${p.display_name}, ${status}` : p.display_name
                }
                onClick={() => router.push(`/app/members/${p.user_id}`)}
                style={{ "--rc": ring } as React.CSSProperties}
                className={`relative block shrink-0 rounded-full ${
                  p.online || p.birthday_in_days != null
                    ? "shadow-[0_0_0_2px_var(--nx-glass-solid),0_0_0_4px_color-mix(in_srgb,var(--rc)_40%,transparent)]"
                    : "shadow-[0_0_0_2px_var(--nx-glass-solid)]"
                }`}
              >
                <Avatar
                  src={p.avatar_url ?? undefined}
                  name={p.display_name}
                  size="lg"
                  className="size-10 md:size-11"
                  userId={p.user_id}
                />
                {p.birthday_in_days != null && (
                  <i className="absolute top-[-6px] right-[-6px] grid size-5 place-items-center rounded-full bg-[var(--nx-glass-solid)] text-[var(--nx-red)]">
                    <Cake aria-hidden className="size-3" />
                  </i>
                )}
              </button>
            </HoverCard.Trigger>
            <HoverCard.Portal>
              <HoverCard.Content
                side="bottom"
                align="end"
                sideOffset={10}
                collisionPadding={16}
                className="z-50 rounded-[22px] border border-[var(--nx-line)] bg-[var(--nx-glass-solid)] p-4 shadow-[0_18px_40px_-16px_rgba(0,0,0,0.5)] data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0 max-md:hidden"
              >
                <ConnectionCard person={p} status={status} />
              </HoverCard.Content>
            </HoverCard.Portal>
          </HoverCard.Root>
        );
      })}
    </div>
  );
}
