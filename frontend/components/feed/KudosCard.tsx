/**
 * @file components/feed/KudosCard.tsx
 * @brief Hero card for a kudos: large sun-ringed recipient avatar, trophy badge,
 *        "Kudos to" headline, quoted message, sender and relative time.
 */
import * as React from "react";
import Link from "next/link";
import { Trophy } from "lucide-react";
import { formatDistanceToNowStrict } from "date-fns";
import { Avatar } from "@/components/ui";

export interface KudosCardProps {
  recipient: {
    id?: string;
    display_name: string;
    avatar_url?: string | null;
  };
  message?: string | null;
  authorName?: string | null;
  createdAt: string;
  pending?: boolean;
  /** Reactions / comment controls rendered under the quote. */
  children?: React.ReactNode;
}

/**
 * @brief Relative time, empty on an invalid date.
 * @param iso ISO timestamp
 * @return e.g. "2 hours ago"
 */
function ago(iso: string): string {
  try {
    return formatDistanceToNowStrict(new Date(iso), { addSuffix: true });
  } catch {
    return "";
  }
}

/**
 * @brief Kudos hero card.
 * @param recipient recipient profile (id enables the profile link)
 * @param message optional message, shown as a quote
 * @param authorName sender display name
 * @param createdAt ISO timestamp
 * @param pending true while optimistic (not yet confirmed)
 * @param children optional footer (reactions, comments)
 * @return article element
 */
export function KudosCard({
  recipient,
  message,
  authorName,
  createdAt,
  pending,
  children,
}: KudosCardProps) {
  const name = recipient.display_name;
  const who = recipient.id ? (
    <Link
      href={`/app/members/${recipient.id}`}
      className="rounded-md outline-none hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      {name}
    </Link>
  ) : (
    name
  );
  return (
    <article
      aria-label={`Kudos to ${name}${authorName ? ` from ${authorName}` : ""}`}
      aria-busy={pending || undefined}
      data-pending={pending ? "true" : undefined}
      className="glass-item text-ink relative flex flex-col gap-4 overflow-hidden rounded-[28px] p-5 data-[pending=true]:opacity-60 md:p-6"
    >
      <span
        aria-hidden="true"
        data-testid="kudos-glow"
        className="pointer-events-none absolute -top-16 -right-10 size-56 rounded-full blur-3xl"
        style={{
          background: "color-mix(in srgb, var(--nx-sun) 22%, transparent)",
        }}
      />
      <div className="relative flex items-center gap-4">
        <span
          className="relative shrink-0 rounded-full p-1"
          style={{ boxShadow: "0 0 0 3px var(--nx-sun)" }}
        >
          <Avatar
            src={recipient.avatar_url ?? undefined}
            name={name}
            className="size-20 text-2xl"
          />
          <span
            data-testid="kudos-trophy"
            aria-hidden="true"
            className="absolute -right-1 -bottom-1 flex size-8 items-center justify-center rounded-full border-2 border-[var(--nx-item)] text-ink dark:text-[var(--nx-surface)]"
            style={{ background: "var(--nx-sun)" }}
          >
            <Trophy className="size-4" />
          </span>
        </span>
        <div className="min-w-0">
          <h3 className="text-2xl leading-tight font-bold break-words">
            Kudos to {who}
          </h3>
        </div>
      </div>
      {message ? (
        <blockquote
          data-testid="kudos-message"
          className="relative border-l-[3px] pl-4 text-lg leading-snug break-words"
          style={{ borderColor: "var(--nx-sun)" }}
        >
          {message}
        </blockquote>
      ) : null}
      <p className="relative text-sm text-[var(--nx-muted)]">
        {authorName ? <>from {authorName} · </> : null}
        <time dateTime={createdAt}>{ago(createdAt)}</time>
      </p>
      {children}
    </article>
  );
}

export default KudosCard;
