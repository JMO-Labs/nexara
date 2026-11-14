/**
 * @file components/feed/KudosCard.tsx
 * @brief Distinct purple card for a kudos: trophy, recipient, message, sender.
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
      className="flex gap-3 rounded-2xl border border-purple-200 bg-purple-100 p-4 text-purple-950 data-[pending=true]:opacity-60"
      data-pending={pending ? "true" : undefined}
    >
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
            className="size-4 shrink-0 text-purple-700"
          />
          <span className="truncate font-bold">{recipient.display_name}</span>
        </div>
        {message ? (
          <p data-testid="kudos-message" className="break-words">
            {message}
          </p>
        ) : null}
        <p className="text-xs text-purple-900">
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
