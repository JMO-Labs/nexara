"use client";
/**
 * @file components/members/PersonCard.tsx
 * @brief Glass card for one person in the directory.
 */
import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { GroupChips } from "@/components/members/GroupChips";
import { statusOf } from "@/components/members/personStatus";
import { useCreateDm } from "@/hooks/useChat";
import type { DirectoryPerson } from "@/lib/api/users";
import { groupColor } from "@/lib/groupColor";

/**
 * @brief Person card with ringed avatar, status, shared groups, actions.
 * @param person directory entry
 * @return article element
 */
export function PersonCard({ person }: { person: DirectoryPerson }) {
  const router = useRouter();
  const dm = useCreateDm();
  const status = statusOf(person);
  const accent = person.shared_groups.find(
    (g) => g.id === person.primary_group_id,
  )?.accent_color;
  const ring = groupColor(person.primary_group_id, accent);

  const message = async () => {
    const channel = await dm.mutateAsync(person.user_id);
    router.push(`/app/chat/${channel.id}`);
  };

  return (
    <article className="glass flex flex-col gap-3 rounded-[28px] p-4">
      <div className="flex items-center gap-3">
        <span
          style={{ "--rc": ring } as React.CSSProperties}
          className="relative block shrink-0 rounded-full shadow-[0_0_0_2px_var(--nx-glass-solid),0_0_0_4px_var(--rc)]"
        >
          <Avatar
            src={person.avatar_url ?? undefined}
            name={person.display_name}
            size="lg"
            className="size-12"
          />
          {person.online && (
            <i
              aria-hidden
              className="absolute right-[-1px] bottom-[-1px] size-3 rounded-full border-2 border-[var(--nx-glass-solid)] bg-[var(--nx-ok)]"
            />
          )}
        </span>
        <div className="min-w-0">
          <h3 className="truncate text-[15px] font-medium text-ink">
            {person.display_name}
          </h3>
          <p className="truncate text-xs text-muted">
            {status || `@${person.username}`}
          </p>
        </div>
      </div>
      <GroupChips groups={person.shared_groups} />
      <div className="mt-auto flex gap-2">
        <button
          type="button"
          onClick={message}
          disabled={dm.isPending}
          aria-label={`Message ${person.display_name}`}
          className="min-h-11 flex-1 rounded-full bg-surface-strong p-2 text-[13px] text-bg disabled:opacity-60"
        >
          Message
        </button>
        <button
          type="button"
          onClick={() => router.push(`/app/members/${person.user_id}`)}
          aria-label={`View ${person.display_name}'s profile`}
          className="glass-item min-h-11 flex-1 rounded-full p-2 text-[13px] text-ink"
        >
          Profile
        </button>
      </div>
    </article>
  );
}
