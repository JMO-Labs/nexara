"use client";
/**
 * @file components/chat/chat-layout/ConversationHeader.tsx
 * @brief Thread header: back, name, presence line, in-conversation search
 *        ("/" focuses, Esc clears), density and details toggles.
 */
import * as React from "react";
import { ArrowLeft, PanelRight, Rows2, Rows3, Search } from "lucide-react";
import { IconButton } from "@/components/ui";
import { useOnline } from "@/stores/presence";
import type { ChatContext } from "@/lib/api/chatContext";
import { localTime, presenceText } from "../format";
import { useOnlineCount } from "../details/GroupDetails";
import { DETAILS_ID, DETAILS_TOGGLE_ID } from "./DetailsHost";

export interface ConversationHeaderProps {
  title: string;
  color: string;
  subtitle?: string;
  context?: ChatContext;
  onBack: () => void;
  query: string;
  onQuery: (q: string) => void;
  /** Matches among loaded messages (shown only while searching). */
  matchCount: number;
  compact: boolean;
  onToggleDensity: () => void;
  detailsOpen: boolean;
  onToggleDetails: () => void;
}

function DmLine({ ctx }: { ctx: Extract<ChatContext, { kind: "dm" }> }) {
  const online = useOnline(ctx.peer.id);
  const status = presenceText(online, ctx.peer.last_seen_at);
  const clock = ctx.peer.local_time_tz
    ? localTime(ctx.peer.local_time_tz)
    : null;
  const first = ctx.peer.display_name.split(" ")[0];
  const parts = [status, clock && `${clock} for ${first}`].filter(Boolean);
  return parts.length ? <>{parts.join(" · ")}</> : null;
}

function GroupLine({ ctx }: { ctx: Extract<ChatContext, { kind: "group" }> }) {
  const n = useOnlineCount(ctx.members.map((m) => m.id));
  const label = ctx.member_count === 1 ? "member" : "members";
  return <>{`${ctx.member_count} ${label} · ${n} online`}</>;
}

/**
 * @param props see ConversationHeaderProps
 * @return header element
 */
export function ConversationHeader(p: ConversationHeaderProps) {
  const searchRef = React.useRef<HTMLInputElement | null>(null);
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t?.closest("input, textarea, select, [contenteditable='true']"))
        return;
      e.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const line =
    p.context?.kind === "dm" ? (
      <DmLine ctx={p.context} />
    ) : p.context?.kind === "group" ? (
      <GroupLine ctx={p.context} />
    ) : null;
  const searching = p.query.trim().length > 0;
  return (
    <header className="flex shrink-0 items-center gap-2 px-2 py-2 md:px-4">
      <IconButton
        aria-label="Back to channels"
        variant="ghost"
        className="size-11 md:hidden"
        onClick={p.onBack}
      >
        <ArrowLeft className="size-5" aria-hidden="true" />
      </IconButton>
      <i
        aria-hidden
        data-testid="thread-dot"
        className="size-2.5 shrink-0 rounded-full"
        style={{ background: p.color }}
      />
      <div className="min-w-0 flex-1">
        <h2 className="truncate text-lg font-semibold">{p.title}</h2>
        <p className="truncate text-xs text-[var(--nx-muted)]">
          {line ?? p.subtitle}
        </p>
      </div>
      <div className="relative">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
        />
        <input
          ref={searchRef}
          type="search"
          aria-label="Search in conversation"
          placeholder="Search"
          value={p.query}
          onChange={(e) => p.onQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape" && p.query) {
              e.preventDefault();
              p.onQuery("");
            }
          }}
          className={`h-10 rounded-full bg-[var(--nx-glass-solid)] pl-9 pr-3 text-sm outline-none placeholder:text-transparent focus:w-40 focus-visible:outline-2 focus-visible:outline-accent sm:w-44 sm:placeholder:text-muted motion-safe:transition-[width] ${searching ? "w-40" : "w-10"}`}
        />
        <span role="status" aria-live="polite" className="sr-only">
          {searching
            ? p.matchCount === 0
              ? "No matches"
              : `${p.matchCount} ${p.matchCount === 1 ? "match" : "matches"}`
            : ""}
        </span>
      </div>
      <IconButton
        aria-label={
          p.compact ? "Use comfortable density" : "Use compact density"
        }
        aria-pressed={p.compact}
        variant="glass"
        size="md"
        className="rounded-full"
        onClick={p.onToggleDensity}
      >
        {p.compact ? (
          <Rows3 className="size-5" aria-hidden="true" />
        ) : (
          <Rows2 className="size-5" aria-hidden="true" />
        )}
      </IconButton>
      <IconButton
        aria-label={p.detailsOpen ? "Close details" : "Open details"}
        aria-expanded={p.detailsOpen}
        id={DETAILS_TOGGLE_ID}
        aria-controls={DETAILS_ID}
        variant="glass"
        size="md"
        className="rounded-full"
        tooltip={p.detailsOpen ? "Close details" : "Open details"}
        onClick={p.onToggleDetails}
      >
        <PanelRight className="size-5" aria-hidden="true" />
      </IconButton>
    </header>
  );
}
