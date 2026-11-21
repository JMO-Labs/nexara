"use client";
/**
 * @file components/home/ConnectionCard.tsx
 * @brief Card body for a person in the home people strip; PeopleStrip shows it
 *        in a Radix HoverCard (portaled, with open/close delays).
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Check, SendHorizontal } from "lucide-react";
import { useCreateDm } from "@/hooks/useChat";
import { postChatMessage } from "@/lib/api/chat";
import type { HomePerson } from "@/lib/api/home";
import { FavoriteButton } from "./FavoriteButton";

/**
 * @brief Connection card: shared context, quick message box (sends into the
 *        DM without leaving Home), Open chat and Profile.
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

  const [text, setText] = React.useState("");
  const [sent, setSent] = React.useState<"ok" | "fail" | null>(null);
  const [sending, setSending] = React.useState(false);

  const message = async () => {
    const channel = await dm.mutateAsync(person.user_id);
    router.push(`/app/chat/${channel.id}`);
  };

  const quickSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = text.trim();
    if (!content) return;
    setSending(true);
    try {
      const channel = await dm.mutateAsync(person.user_id);
      await postChatMessage(channel.id, content);
      setText("");
      setSent("ok");
    } catch {
      setSent("fail");
    } finally {
      setSending(false);
    }
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
      <form
        onSubmit={quickSend}
        className="mb-2 flex items-center gap-1.5 rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_7%,transparent)] py-1 pr-1 pl-3.5"
      >
        <input
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setSent(null);
          }}
          aria-label={`Message ${first}`}
          placeholder={`Message ${first}`}
          autoComplete="off"
          maxLength={4000}
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--nx-faint)]"
        />
        <button
          type="submit"
          aria-label="Send"
          disabled={!text.trim() || sending}
          className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-strong text-bg disabled:opacity-40"
        >
          <SendHorizontal className="size-4" aria-hidden />
        </button>
      </form>
      {sent === "fail" && (
        <p role="alert" className="mb-2 text-xs text-destructive">
          Couldn't send. Try again.
        </p>
      )}
      {sent === "ok" && (
        <p
          role="status"
          className="mb-2 flex items-center gap-1 text-xs text-[var(--nx-muted)]"
        >
          <Check className="size-3.5 text-[var(--nx-ok)]" aria-hidden /> Sent to{" "}
          {first}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={message}
          className="glass-item flex-1 rounded-full p-2 text-sm font-medium text-ink"
        >
          Open chat
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
