"use client";
/**
 * @file plugins/example-trivia/components/StatsDetail.tsx
 * @brief Current user's detailed trivia stats with a share-link button.
 */
import { Share2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToasts } from "@/stores/toasts";
import { useMyStats } from "../hooks/useTrivia";

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString() : "—";

/** @brief URL that opens the trivia leaderboard on the current page. */
export function leaderboardLink(): string {
  const { origin, pathname } = window.location;
  return `${origin}${pathname}?trivia=leaderboard`;
}

/** @brief Detailed stats sheet. @return stats panel */
export function StatsDetail() {
  const { data, isLoading, isError } = useMyStats();
  const push = useToasts((s) => s.push);

  if (isLoading)
    return (
      <p role="status" className="text-sm">
        Loading your stats…
      </p>
    );
  if (isError || !data)
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your stats. Please try again later.
      </p>
    );

  const share = async () => {
    try {
      await navigator.clipboard.writeText(leaderboardLink());
      push({ variant: "success", message: "Leaderboard link copied" });
    } catch {
      push({ variant: "danger", message: "Couldn't copy the link" });
    }
  };

  const rows: [string, string][] = [
    ["Rank", `#${data.rank}`],
    ["Current streak", String(data.streak)],
    ["Personal best streak", String(data.best_streak)],
    ["Total correct", String(data.total_correct)],
    ["Total answers", `${data.total_answers} answers`],
    ["Correct", `${Math.round(data.percentage_correct)}%`],
    ["Days participated", `${data.days_participated} days`],
    ["First answer", fmtDate(data.first_answer_at)],
    ["Last answer", fmtDate(data.last_answer_at)],
  ];

  return (
    <section aria-label="My trivia stats" className="mt-4 space-y-3">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-ink/70">{k}</dt>
            <dd className="font-semibold">{v}</dd>
          </div>
        ))}
      </dl>
      <Button variant="outline" className="min-h-11" onClick={share}>
        <Share2 aria-hidden className="size-4" />
        Share leaderboard
      </Button>
    </section>
  );
}

export default StatsDetail;
