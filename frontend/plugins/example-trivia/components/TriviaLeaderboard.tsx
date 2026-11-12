"use client";
/**
 * @file plugins/example-trivia/components/TriviaLeaderboard.tsx
 * @brief Paginated leaderboard dialog (25 per page) with the current user's
 *        row highlighted and an expandable detailed-stats panel.
 */
import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { useSession } from "@/stores/session";
import { useLeaderboard } from "../hooks/useTrivia";
import { useTriviaWebSocket } from "../hooks/useTriviaWebSocket";
import { StatsDetail } from "./StatsDetail";

export interface TriviaLeaderboardProps {
  open: boolean;
  onClose: () => void;
}

const COLS = ["Rank", "User Name", "Current Streak", "Total Correct"];

/** @brief Leaderboard modal. @param props open state and close handler */
export function TriviaLeaderboard({ open, onClose }: TriviaLeaderboardProps) {
  const [page, setPage] = useState(1);
  const [showStats, setShowStats] = useState(false);
  const meId = useSession((s) => s.user?.id);
  const { data, isLoading, isError } = useLeaderboard(page);
  useTriviaWebSocket(open);
  const pages = Math.max(1, data?.pages ?? 1);

  return (
    <Modal open={open} onClose={onClose} title="Trivia leaderboard" size="lg">
      {isError ? (
        <p role="alert" className="text-sm text-destructive">
          Couldn&apos;t load the leaderboard. Please try again later.
        </p>
      ) : isLoading || !data ? (
        <p role="status" className="text-sm">
          Loading leaderboard…
        </p>
      ) : (
        <table className="w-full text-sm">
          <caption className="sr-only">
            Top players by streak, then total correct
          </caption>
          <thead>
            <tr>
              {COLS.map((c) => (
                <th key={c} scope="col" className="px-2 py-1 text-left">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.entries.map((e) => {
              const me = e.user_id === meId;
              return (
                <tr
                  key={e.user_id}
                  aria-current={me ? "page" : undefined}
                  className={cn(me && "bg-accent/20 font-semibold")}
                >
                  <td className="px-2 py-1">{e.rank}</td>
                  <td className="px-2 py-1">{e.user_name}</td>
                  <td className="px-2 py-1">{e.streak}</td>
                  <td className="px-2 py-1">{e.total_correct}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <nav
        aria-label="Leaderboard pages"
        className="flex items-center justify-between gap-2"
      >
        <Button
          variant="outline"
          className="min-h-11"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </Button>
        <span aria-live="polite" className="text-sm">
          Page {page} of {pages}
        </span>
        <Button
          variant="outline"
          className="min-h-11"
          disabled={page >= pages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </Button>
      </nav>
      <Button
        variant="ghost"
        className="min-h-11"
        aria-expanded={showStats}
        onClick={() => setShowStats((s) => !s)}
      >
        View My Detailed Stats
      </Button>
      {showStats ? <StatsDetail /> : null}
    </Modal>
  );
}

export default TriviaLeaderboard;
