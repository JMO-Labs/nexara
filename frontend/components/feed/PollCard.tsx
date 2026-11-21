"use client";
/**
 * @file components/feed/PollCard.tsx
 * @brief Inline poll on a post: tap to vote (single/yes-no), tick then Vote
 *        (multiple). Results show as bars once voted, closed, or always-visible.
 */
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { Button } from "@/components/ui";
import { votePoll } from "@/lib/api/polls";
import type { Poll } from "@/lib/api/posts";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

/**
 * @brief Poll block.
 * @param poll poll payload from the post
 * @return poll element
 */
export function PollCard({ poll }: { poll: Poll }) {
  const qc = useQueryClient();
  const [picked, setPicked] = React.useState<string[]>([]);
  const [changing, setChanging] = React.useState(false);
  const voted = (poll.user_vote?.length ?? 0) > 0;
  const expired = !!poll.expires_at && Date.parse(poll.expires_at) < Date.now();
  const ended = poll.closed || expired;
  const multi = poll.poll_type === "multiple";
  const showResults =
    !changing &&
    (ended ||
      (voted && poll.result_visibility !== "after_expiry") ||
      poll.result_visibility === "always");
  const canVote = !ended && (!voted || changing);

  const vote = useMutation({
    mutationFn: (ids: string[]) => votePoll(poll.id, ids),
    onSuccess: () => {
      setChanging(false);
      setPicked([]);
      void qc.invalidateQueries({ queryKey: qk.feed.all() });
      void qc.invalidateQueries({ queryKey: qk.home.feed() });
    },
  });

  const onOption = (id: string) => {
    if (!canVote || vote.isPending) return;
    if (!multi) return vote.mutate([id]);
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  };

  const total = Math.max(poll.total_votes, 1);
  const options = [...poll.options].sort((a, b) => a.position - b.position);

  return (
    <fieldset className="glass-item mt-3 flex flex-col gap-2 rounded-[22px] p-3.5">
      <legend className="sr-only">Poll</legend>
      <p className="text-[15px] font-medium">{poll.question}</p>
      {options.map((o) => {
        const mine = poll.user_vote?.includes(o.id) ?? false;
        const on = picked.includes(o.id);
        const pct = Math.round((o.vote_count / total) * 100);
        return (
          <button
            key={o.id}
            type="button"
            disabled={!canVote}
            aria-pressed={multi ? on : undefined}
            onClick={() => onOption(o.id)}
            className={cn(
              "relative flex items-center gap-2 overflow-hidden rounded-full px-4 py-2 text-left text-sm outline-none transition-colors focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-default",
              canVote &&
                "bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] hover:bg-[color-mix(in_srgb,var(--nx-ink)_12%,transparent)]",
              on && "ring-2 ring-[var(--nx-blue)]",
              showResults &&
                "bg-[color-mix(in_srgb,var(--nx-ink)_5%,transparent)]",
            )}
          >
            {showResults && (
              <span
                aria-hidden
                className={cn(
                  "absolute inset-y-0 left-0 rounded-full transition-[width] duration-500",
                  mine
                    ? "bg-[color-mix(in_srgb,var(--nx-blue)_35%,transparent)]"
                    : "bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)]",
                )}
                style={{ width: `${pct}%` }}
              />
            )}
            <span className="relative flex-1">{o.label}</span>
            {mine && (
              <Check aria-label="Your vote" className="relative size-4" />
            )}
            {showResults && (
              <span className="relative text-xs tabular-nums text-muted">
                {pct}%
              </span>
            )}
          </button>
        );
      })}
      <div className="flex items-center gap-3 text-xs text-muted">
        <span>
          {poll.total_votes} {poll.total_votes === 1 ? "vote" : "votes"}
          {ended
            ? " · Final results"
            : poll.expires_at
              ? ` · Ends ${new Date(poll.expires_at).toLocaleDateString()}`
              : ""}
          {multi && canVote ? " · Pick any" : ""}
        </span>
        <span className="grow" />
        {multi && canVote && (
          <Button
            size="sm"
            disabled={picked.length === 0}
            loading={vote.isPending}
            onClick={() => vote.mutate(picked)}
          >
            Vote
          </Button>
        )}
        {voted && !ended && !changing && (
          <Button size="sm" variant="ghost" onClick={() => setChanging(true)}>
            Change vote
          </Button>
        )}
        {changing && (
          <Button size="sm" variant="ghost" onClick={() => setChanging(false)}>
            Cancel
          </Button>
        )}
      </div>
      {vote.isError && (
        <p role="alert" className="text-xs text-destructive">
          {vote.error instanceof Error ? vote.error.message : "Vote failed."}
        </p>
      )}
    </fieldset>
  );
}
