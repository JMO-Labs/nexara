"use client";
/**
 * @file components/chat/chat-layout/ThreadPane.tsx
 * @brief Active conversation: header (back, title, details toggle), messages,
 *        typing indicator and composer. Optional details side pane.
 */
import type { ComponentProps } from "react";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { IconButton } from "@/components/ui";
import { MessageList } from "../MessageList";
import { Composer } from "../Composer";
import { TypingIndicator } from "../TypingIndicator";

export interface ThreadPaneProps {
  title: string;
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
  onBack,
  detailsOpen,
  onToggleDetails,
  list,
  typingCount,
  composer,
}: ThreadPaneProps) {
  return (
    <section
      aria-label={title}
      className="flex min-h-0 min-w-0 flex-col overflow-hidden"
    >
      <header className="bg-surface flex shrink-0 items-center gap-2 border-b border-border px-2 py-2 md:px-4">
        <IconButton
          aria-label="Back to channels"
          variant="ghost"
          className="size-11 md:hidden"
          onClick={onBack}
        >
          <ArrowLeft className="size-5" aria-hidden="true" />
        </IconButton>
        <h2 className="min-w-0 flex-1 truncate text-lg font-semibold">
          {title}
        </h2>
        <IconButton
          aria-label={detailsOpen ? "Close thread panel" : "Open thread panel"}
          aria-pressed={detailsOpen}
          variant="ghost"
          className="hidden md:inline-flex"
          onClick={onToggleDetails}
        >
          <ChevronRight
            className={`size-5 ${detailsOpen ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </IconButton>
      </header>
      <MessageList {...list} />
      <TypingIndicator count={typingCount} />
      <Composer {...composer} />
    </section>
  );
}

/**
 * @brief Placeholder details column (desktop only).
 * @return aside element
 */
export function DetailsPane() {
  return (
    <aside
      aria-label="Details"
      className="bg-surface hidden min-h-0 min-w-0 flex-col border-l border-border md:flex"
    >
      <h2 className="shrink-0 border-b border-border px-4 py-3 text-sm font-semibold">
        Details
      </h2>
      <p className="text-muted flex-1 overflow-auto p-4 text-sm">
        Thread details and conversation info will appear here.
      </p>
    </aside>
  );
}
