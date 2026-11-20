/**
 * @file components/feed/KudosCard.tsx
 * @brief Glass-item card for a kudos (sun accent bar): trophy, recipient, message, sender.
 */
import { Trophy } from "lucide-react";
import { Avatar } from "@/components/ui";

export interface KudosCardProps {
  recipient: {
    display_name: string;
    avatar_url?: string | null;
  };
  message?: string | null;
  authorName?: string | null;
  createdAt: string;
  pending?: boolean;
}

/**
 * @brief Kudos card.
 * @param recipient recipient profile
 * @param message optional message
 * @param authorName sender display name
 * @param createdAt ISO timestamp
 * @param pending true while optimistic (not yet confirmed)
 * @return article element
 */
export function KudosCard({
  recipient,
  message,
  authorName,
  createdAt,
  pending,
}: KudosCardProps) {
  return (
    <article
      aria-busy={pending || undefined}
      className="glass-item text-ink relative flex gap-3 overflow-hidden rounded-[24px] p-4 pl-5 data-[pending=true]:opacity-60"
      data-pending={pending ? "true" : undefined}
    >
      <span
        aria-hidden="true"
        data-testid="kudos-bar"
        className="absolute inset-y-0 left-0 w-[3px]"
        style={{ background: "var(--nx-sun)" }}
      />
      <Avatar
        src={recipient.avatar_url ?? undefined}
        name={recipient.display_name}
        size="lg"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center gap-2">
          <Trophy
            data-testid="kudos-trophy"
            aria-hidden="true"
            className="size-4 shrink-0"
            style={{ color: "var(--nx-sun)" }}
          />
          <span className="truncate font-bold">{recipient.display_name}</span>
        </div>
        {message ? (
          <p data-testid="kudos-message" className="break-words">
            {message}
          </p>
        ) : null}
        <p className="text-xs text-[var(--nx-muted)]">
          {authorName ? `${authorName} · ` : ""}
          <time dateTime={createdAt}>
            {new Date(createdAt).toLocaleDateString()}
          </time>
        </p>
      </div>
    </article>
  );
}

export default KudosCard;
