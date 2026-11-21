"use client";
/**
 * @file components/home/ConnectionCard.tsx
 * @brief Card body for a person in the home people strip; PeopleStrip shows it
 *        in a Radix HoverCard (portaled, with open/close delays).
 */
import { useRouter } from "next/navigation";
import { useCreateDm } from "@/hooks/useChat";
import type { HomePerson } from "@/lib/api/home";
import { FavoriteButton } from "./FavoriteButton";

/**
 * @brief Connection card with shared context and Message/Profile actions.
 * @param person The person shown.
 * @param status Human status line ("" to omit).
 * @return Card body.
 */
export function ConnectionCard({
  person,
  status,
}: {
  person: HomePerson;
  status: string;
}) {
  const router = useRouter();
  const dm = useCreateDm();
  const first = person.display_name.split(" ")[0];

  const message = async () => {
    const channel = await dm.mutateAsync(person.user_id);
    router.push(`/app/chat/${channel.id}`);
  };

  return (
    <div className="w-[260px] text-left text-[var(--nx-ink)]">
      <div className="flex items-start justify-between gap-2">
        <strong className="block text-[15px] font-medium">
          {person.display_name}
        </strong>
        <FavoriteButton
          userId={person.user_id}
          name={person.display_name}
          className="-mt-1 -mr-1 size-8"
        />
      </div>
      <span className="my-1.5 mb-2.5 inline-block rounded-full border border-dashed border-[var(--nx-line)] px-[9px] py-0.5 text-xs text-[var(--nx-faint)]">
        Add how you know {first}
      </span>
      <ul className="mb-3 grid gap-1.5 text-[13px] text-[var(--nx-muted)]">
        {person.shared_groups.map((g) => (
          <li key={g.id}>{g.name}</li>
        ))}
        {person.shared_events_30d > 0 && (
          <li>{person.shared_events_30d} shared events this month</li>
        )}
        {status && <li>{status}</li>}
      </ul>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={message}
          className="flex-1 rounded-full bg-surface-strong p-2 text-sm font-medium text-bg"
        >
          Message
        </button>
        <button
          type="button"
          onClick={() => router.push(`/app/members/${person.user_id}`)}
          className="glass-item flex-1 rounded-full p-2 text-sm font-medium text-ink"
        >
          Profile
        </button>
      </div>
    </div>
  );
}
