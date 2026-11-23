"use client";
/**
 * @file components/chat/ConversationStarters.tsx
 * @brief Up to three soft suggestion chips for a quiet conversation (< 5
 *        messages). Clicking prefills the composer; nothing is sent.
 */
import { useActivePrompts } from "@/hooks/useActivePrompts";
import type { ChatContext } from "@/lib/api/chatContext";
import { inDays } from "./format";

export const STARTER_MESSAGE_LIMIT = 5;

export interface Starter {
  label: string;
  text: string;
}

export interface ConversationStartersProps {
  messageCount: number;
  context?: ChatContext;
  onPick: (text: string) => void;
}

/**
 * @brief Build the chip list from available signals.
 * @param daily today's daily question title or null
 * @param context details payload
 * @return at most 3 starters (photo fallback when none apply)
 */
export function buildStarters(
  daily: string | null,
  context?: ChatContext,
): Starter[] {
  const out: Starter[] = [];
  if (daily) {
    out.push({
      label: "Answer today's question together",
      text: `${daily} `,
    });
  }
  const event =
    context?.kind === "dm" ? context.upcoming_events[0] : context?.next_event;
  if (event) {
    out.push({ label: `Plan for ${event.title}`, text: `${event.title}: ` });
  }
  if (
    context?.kind === "dm" &&
    context.peer.birthday_in_days !== null &&
    context.peer.birthday_in_days <= 7
  ) {
    const first = context.peer.display_name.split(" ")[0];
    out.push({
      label: `${first}'s birthday is ${inDays(context.peer.birthday_in_days)}`,
      text: `Anything planned for your birthday, ${first}? `,
    });
  }
  if (out.length === 0) {
    out.push({
      label: "Share a photo",
      text: "Here's a photo I wanted to share: ",
    });
  }
  return out.slice(0, 3);
}

/**
 * @param props see ConversationStartersProps
 * @return chip group or null once the conversation is going
 */
export function ConversationStarters({
  messageCount,
  context,
  onPick,
}: ConversationStartersProps) {
  const prompts = useActivePrompts();
  if (messageCount >= STARTER_MESSAGE_LIMIT) return null;
  const daily =
    prompts.data?.find((p) => p.prompt.prompt_type === "daily_question")?.prompt
      .title ?? null;
  const starters = buildStarters(daily, context);
  return (
    <ul
      aria-label="Conversation starters"
      className="mx-auto flex w-full max-w-[760px] list-none flex-wrap justify-center gap-2 px-4 pb-2"
    >
      {starters.map((s) => (
        <li key={s.label}>
          <button
            type="button"
            onClick={() => onPick(s.text)}
            className="min-h-9 rounded-full bg-[var(--nx-bubble)] px-3.5 text-sm outline-none hover:bg-[var(--nx-item)] focus-visible:outline-2 focus-visible:outline-accent"
          >
            {s.label}
          </button>
        </li>
      ))}
    </ul>
  );
}
