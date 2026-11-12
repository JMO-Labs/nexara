"use client";
/**
 * @file plugins/example-trivia/components/TriviaWidget.tsx
 * @brief Sidebar widget: today's multiple-choice question, answer
 *        submission with toast feedback, streak and leaderboard entry point.
 */
import { useEffect, useState } from "react";
import type { KeyboardEvent } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { useToasts } from "@/stores/toasts";
import type { PluginComponentProps } from "@/lib/plugins/plugin-loader";
import {
  useSubmitAnswer,
  useTodayQuestion,
  type AnswerResult,
  type TriviaOption,
} from "../hooks/useTrivia";
import { TriviaLeaderboard } from "./TriviaLeaderboard";

const LETTERS = ["A", "B", "C", "D"];
const PULSE = "rounded bg-ink/10 motion-safe:animate-pulse";

function optionClass(selected: boolean, result: AnswerResult | null) {
  if (selected && result)
    return result.correct
      ? "border-green-700 bg-green-100 text-green-900"
      : "border-red-700 bg-red-100 text-red-900";
  return selected
    ? "border-accent bg-accent/20 font-semibold"
    : "border-ink/30";
}

function sharedBoardLink(): boolean {
  if (typeof window === "undefined") return false;
  const p = new URLSearchParams(window.location.search);
  return p.get("trivia") === "leaderboard";
}

function Streak({ n }: { n?: number }) {
  if (!n) return null;
  return <p className="text-sm font-medium">{n}-day streak</p>;
}

/** @brief Trivia sidebar widget. @param props slot props from PluginSlot */
export function TriviaWidget({ pluginId }: PluginComponentProps) {
  const { data, isLoading, isError, refetch } = useTodayQuestion();
  const submit = useSubmitAnswer();
  const push = useToasts((s) => s.push);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  // Shared links (?trivia=leaderboard) open the board. Client-only plugin.
  const [showBoard, setShowBoard] = useState(sharedBoardLink);

  useEffect(() => {
    if (isError)
      push({ variant: "danger", message: "Couldn't load today's trivia" });
  }, [isError, push]);

  const board = showBoard ? (
    <TriviaLeaderboard open onClose={() => setShowBoard(false)} />
  ) : null;
  const boardBtn = (
    <Button
      variant="ghost"
      className="min-h-11"
      onClick={() => setShowBoard(true)}
    >
      View Leaderboard
    </Button>
  );

  if (isLoading)
    return (
      <Card className="p-4 shadow-sm">
        <div role="status" aria-label="Loading trivia" className="space-y-2">
          <div className={cn(PULSE, "h-4 w-3/4")} />
          <div className={cn(PULSE, "h-10")} />
          <div className={cn(PULSE, "h-10")} />
        </div>
      </Card>
    );

  if (isError || !data)
    return (
      <Card className="space-y-2 p-4 shadow-sm">
        <p role="alert" className="text-sm">
          Couldn&apos;t load today&apos;s question.
        </p>
        <Button className="min-h-11" onClick={() => void refetch()}>
          Retry
        </Button>
      </Card>
    );

  const letter = (o: TriviaOption) =>
    LETTERS[data.options.indexOf(o)] ?? String(data.options.indexOf(o) + 1);

  if (data.answered_today && !result) {
    const chosen = data.options.find((o) => o.id === data.user_answer_id);
    return (
      <Card className="space-y-2 border border-ink/10 p-4 shadow-sm">
        <h2 className="font-semibold">Daily trivia</h2>
        <p className="text-sm">Already answered today.</p>
        {chosen ? (
          <p className="text-sm">
            Your answer: {letter(chosen)}. {chosen.text}
          </p>
        ) : null}
        <Streak n={data.streak} />
        {boardBtn}
        {board}
      </Card>
    );
  }

  const locked = result !== null || submit.isPending;
  const doSubmit = () => {
    if (!selected || locked) return;
    submit.mutate(
      { question_id: data.question_id, answer_id: selected },
      {
        onSuccess: (r) => {
          setResult(r);
          push(
            r.correct
              ? { variant: "success", message: "Correct! +1 streak" }
              : { variant: "danger", message: "Incorrect" },
          );
        },
        onError: () =>
          push({
            variant: "danger",
            message: "Couldn't submit your answer. Please try again.",
          }),
      },
    );
  };
  const onKeyDown = (e: KeyboardEvent<HTMLFormElement>) => {
    if (e.key === "Enter" && selected) {
      e.preventDefault();
      doSubmit();
    }
  };

  return (
    <Card
      data-plugin-id={pluginId}
      className="space-y-3 border border-ink/10 p-4 shadow-sm"
    >
      <form
        onKeyDown={onKeyDown}
        onSubmit={(e) => {
          e.preventDefault();
          doSubmit();
        }}
        className="space-y-3"
      >
        <h2 className="sr-only">Daily trivia</h2>
        <p id="trivia-q" className="font-semibold">
          {data.text}
        </p>
        <Streak n={result?.streak ?? data.streak} />
        <div
          role="group"
          aria-label="Answer options"
          aria-describedby="trivia-q"
          aria-busy={submit.isPending}
          className="grid gap-2"
        >
          {data.options.map((o) => (
            <button
              key={o.id}
              type="button"
              aria-label={`Option ${letter(o)}: ${o.text}`}
              aria-pressed={selected === o.id}
              disabled={locked}
              onClick={() => setSelected(o.id)}
              className={cn(
                "min-h-11 rounded-xl border-2 px-3 text-left text-sm",
                "focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed",
                optionClass(selected === o.id, result),
              )}
            >
              <span aria-hidden className="mr-2 font-bold">
                {letter(o)}
              </span>
              {o.text}
            </button>
          ))}
        </div>
        {result ? null : (
          <Button
            type="submit"
            className="min-h-11 w-full"
            disabled={!selected || locked}
            loading={submit.isPending}
          >
            Submit
          </Button>
        )}
      </form>
      {boardBtn}
      {board}
    </Card>
  );
}

export default TriviaWidget;
