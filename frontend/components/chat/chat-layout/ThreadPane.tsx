"use client";
/**
 * @file components/chat/chat-layout/ThreadPane.tsx
 * @brief Active conversation: header (presence, search, toggles), messages in
 *        a centered reading column, starters, typing indicator and composer.
 */
import * as React from "react";
import type { ComponentProps } from "react";
import type { ChatContext } from "@/lib/api/chatContext";
import { MessageList } from "../MessageList";
import { Composer, type ComposerHandle } from "../Composer";
import { ConversationStarters } from "../ConversationStarters";
import { TypingIndicator } from "../TypingIndicator";
import { ConversationHeader } from "./ConversationHeader";
import { readDensity, writeDensity, type Density } from "./helpers";

export interface ThreadPaneProps {
  title: string;
  /** Group colour for the header dot. */
  color?: string;
  /** Fallback header line when no presence/context is available. */
  subtitle?: string;
  /** Details payload (presence line, starters). */
  context?: ChatContext;
  onBack: () => void;
  detailsOpen: boolean;
  onToggleDetails: () => void;
  list: ComponentProps<typeof MessageList>;
  typingCount: number;
  composer: ComponentProps<typeof Composer>;
}

/**
 * @brief Conversation column.
 * @param props see ThreadPaneProps
 * @return section element
 */
export function ThreadPane({
  title,
  color = "var(--nx-blue)",
  subtitle,
  context,
  onBack,
  detailsOpen,
  onToggleDetails,
  list,
  typingCount,
  composer,
}: ThreadPaneProps) {
  const composerRef = React.useRef<ComposerHandle | null>(null);
  // Persisted so the choice survives the per-channel remount (key={id}).
  const [density, setDensityState] = React.useState<Density>(readDensity);
  const [query, setQuery] = React.useState("");
  const setDensity = (d: Density) => {
    setDensityState(d);
    writeDensity(d);
  };
  const compact = density === "compact";
  const q = query.trim().toLowerCase();
  const shown = React.useMemo(
    () =>
      q
        ? list.messages.filter(
            (m) => !m.deleted && m.content.toLowerCase().includes(q),
          )
        : list.messages,
    [list.messages, q],
  );
  const startConversation = () => {
    composerRef.current?.focus();
    list.onStartConversation?.();
  };
  return (
    <section
      aria-label={title}
      className="glass flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[32px]"
    >
      <ConversationHeader
        title={title}
        color={color}
        subtitle={subtitle}
        context={context}
        onBack={onBack}
        query={query}
        onQuery={setQuery}
        matchCount={shown.length}
        compact={compact}
        onToggleDensity={() => setDensity(compact ? "comfortable" : "compact")}
        detailsOpen={detailsOpen}
        onToggleDetails={onToggleDetails}
      />
      <MessageList
        {...list}
        messages={shown}
        highlight={q}
        density={density}
        onStartConversation={startConversation}
      />
      {!q && !list.isLoading && !list.isError && (
        <ConversationStarters
          messageCount={list.messages.length}
          context={context}
          onPick={(t) => composerRef.current?.prefill(t)}
        />
      )}
      <TypingIndicator count={typingCount} />
      <Composer ref={composerRef} {...composer} />
    </section>
  );
}
