"use client";
/**
 * @file components/feed/PollCard.tsx
 * @brief Hero poll on a post: headline question with chart badge, big lettered
 *        option rows (tap to vote, or tick then Vote for multiple), animated
 *        result bars once voted/closed/always-visible. Honors reduced motion.
 */
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Check } from "lucide-react";
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
  const [now] = React.useState(() => Date.now());
  const expired = !!poll.expires_at && Date.parse(poll.expires_at) < now;
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

  const [grown, setGrown] = React.useState(false);
  React.useEffect(() => {
    if (!showResults) return;
    const id = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(id);
  }, [showResults]);

  const total = Math.max(poll.total_votes, 1);
  const options = [...poll.options].sort((a, b) => a.position - b.position);

  return (
    <fieldset
      aria-label={`Poll: ${poll.question}`}
      className="glass-item relative mt-3 flex flex-col gap-3 overflow-hidden rounded-[28px] p-5 md:p-6"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex size-10 shrink-0 items-center justify-center rounded-2xl text-[var(--nx-surface)] dark:text-[var(--nx-surface)]"
          style={{ background: "var(--nx-accent)" }}
        >
          <BarChart3 className="size-5" />
        </span>
        <p className="text-xl leading-snug font-bold break-words text-ink">
          {poll.question}
        </p>
      </div>
      {options.map((o, i) => {
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
              "relative flex min-h-14 items-center gap-3 overflow-hidden rounded-2xl border border-[var(--nx-item-edge)] px-4 py-3 text-left text-base text-ink outline-none transition-colors focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-default",
              canVote &&
                "bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] hover:bg-[color-mix(in_srgb,var(--nx-ink)_12%,transparent)]",
              on && "ring-2 ring-[var(--nx-accent)]",
              showResults &&
                "bg-[color-mix(in_srgb,var(--nx-ink)_5%,transparent)]",
            )}
          >
            {showResults && (
              <span
                aria-hidden
                data-testid="poll-bar"
                className={cn(
                  "absolute inset-y-0 left-0 transition-[width] duration-700 ease-out motion-reduce:transition-none",
                  mine
                    ? "bg-[color-mix(in_srgb,var(--nx-accent)_30%,transparent)]"
                    : "bg-[color-mix(in_srgb,var(--nx-accent)_12%,transparent)]",
                )}
                style={{ width: grown ? `${pct}%` : "0%" }}
              />
            )}
            <span
              aria-hidden
              className="relative flex size-7 shrink-0 items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)] text-xs font-bold"
            >
              {String.fromCharCode(65 + i)}
            </span>
            <span className="relative flex-1 font-medium">{o.label}</span>
            {mine && (
              <Check
                aria-label="Your vote"
                className="relative size-5 text-accent"
              />
            )}
            {showResults && (
              <span className="relative text-sm font-semibold tabular-nums">
                {pct}%
              </span>
            )}
          </button>
        );
      })}
      <div className="flex items-center gap-3 text-xs text-muted">
        <span>
          {showResults
            ? `${poll.total_votes} ${poll.total_votes === 1 ? "vote" : "votes"}`
            : "Vote to see results"}
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
