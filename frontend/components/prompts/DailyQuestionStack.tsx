"use client";
/**
 * @file components/prompts/DailyQuestionStack.tsx
 * @brief One compact "Questions of the day" card: a tight row per active daily
 *        question that expands inline to the full DailyQuestionCard.
 */
import * as React from "react";
import { useReducedMotion } from "framer-motion";
import { ChevronDown, MessageCircleQuestion } from "lucide-react";
import { Card } from "@/components/ui";
import { DailyQuestionCard } from "@/components/prompts/DailyQuestionCard";
import { dayLabel } from "@/components/prompts/stackPlacement";
import { useInfinitePromptResponses } from "@/hooks/usePromptResponses";
import { OPEN_QOTD_EVENT, selectUnanswered, useQotd } from "@/stores/qotd";
import { cn } from "@/lib/utils";
import type { PromptPost } from "@/lib/api/prompts";

interface RowProps {
  post: PromptPost;
  open: boolean;
  onToggle: () => void;
  reduced: boolean;
}

/** @brief One question row (+ expanded card). Reports answered status. */
function Row({ post, open, onToggle, reduced }: RowProps) {
  const first = useInfinitePromptResponses(post.id).data?.pages[0];
  const answered = first?.answered;
  const setAnswered = useQotd((s) => s.setAnswered);
  React.useEffect(() => {
    if (answered !== undefined) setAnswered(post.id, answered === true);
  }, [answered, post.id, setAnswered]);
  const count = first?.locked ? (first.count ?? 0) : post.response_count;
  const panel = `qotd-panel-${post.id}`;
  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panel}
        onClick={onToggle}
        className="hover:bg-surface flex min-h-11 w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
      >
        <span className="max-w-[9rem] shrink-0 truncate text-xs text-muted">
          {post.subgroup_name ?? "Everyone"} · {dayLabel(post.fired_at)}
        </span>
        <span className="min-w-0 flex-1 truncate font-medium">
          {post.question_text ?? post.prompt.body}
        </span>
        {answered === false && (
          <span className="shrink-0 rounded-full bg-surface-strong px-2 py-0.5 text-xs font-semibold text-bg">
            Answer
          </span>
        )}
        {answered === true && (
          <span className="shrink-0 text-xs whitespace-nowrap text-muted">
            ✓ Answered · {count} {count === 1 ? "answer" : "answers"}
          </span>
        )}
        <ChevronDown
          aria-hidden="true"
          className={cn(
            "size-4 shrink-0 text-muted",
            !reduced && "transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      <div id={panel} hidden={!open} className="pt-2 pb-1">
        {open && <DailyQuestionCard post={post} embedded />}
      </div>
    </li>
  );
}

/**
 * @brief Collapsed-by-default stack of daily questions.
 * @param posts daily_question prompt posts (any order)
 * @return card element, or null when empty
 */
export function DailyQuestionStack({ posts }: { posts: PromptPost[] }) {
  const reduced = useReducedMotion() ?? false;
  const sorted = React.useMemo(
    () => [...posts].sort((a, b) => b.fired_at.localeCompare(a.fired_at)),
    [posts],
  );
  const ids = React.useMemo(() => sorted.map((p) => p.id), [sorted]);
  const [open, setOpen] = React.useState<Set<string>>(new Set());
  const focusRef = React.useRef<string | null>(null);
  const ref = React.useRef<HTMLDivElement>(null);
  const setIds = useQotd((s) => s.setIds);

  React.useEffect(() => {
    setIds(ids);
    return () => setIds(null);
  }, [ids, setIds]);

  React.useEffect(() => {
    const onOpen = () => {
      const target = selectUnanswered(useQotd.getState())?.[0];
      ref.current?.scrollIntoView?.({
        block: "start",
        behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")
          .matches
          ? "auto"
          : "smooth",
      });
      if (!target) return;
      setOpen((s) => new Set(s).add(target));
      focusRef.current = target;
    };
    window.addEventListener(OPEN_QOTD_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_QOTD_EVENT, onOpen);
  }, []);

  React.useEffect(() => {
    const focusId = focusRef.current;
    if (!focusId) return;
    const ta = document.querySelector<HTMLElement>(
      `#qotd-panel-${focusId} textarea`,
    );
    if (ta) {
      ta.focus({ preventScroll: true });
      focusRef.current = null;
    }
  }, [open]);

  if (sorted.length === 0) return null;
  const allOpen = open.size === sorted.length;
  const toggle = (id: string) =>
    setOpen((s) => {
      const n = new Set(s);
      if (!n.delete(id)) n.add(id);
      return n;
    });

  return (
    <Card
      ref={ref}
      data-testid="qotd-stack"
      role="region"
      aria-label="Questions of the day"
      className="flex scroll-mt-2 flex-col gap-1 border-l-4 border-accent p-3"
    >
      <div className="flex items-center gap-2 px-2">
        <MessageCircleQuestion
          className="size-4 text-muted"
          aria-hidden="true"
        />
        <h2 className="text-sm font-semibold">Questions of the day</h2>
        <span
          aria-label={`${sorted.length} questions`}
          className="rounded-full bg-accent px-2 text-xs font-semibold text-accent-foreground"
        >
          {sorted.length}
        </span>
        <button
          type="button"
          onClick={() =>
            setOpen(allOpen ? new Set() : new Set(sorted.map((p) => p.id)))
          }
          className="ml-auto min-h-8 rounded px-2 text-xs text-muted underline-offset-2 hover:underline focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
        >
          {allOpen ? "Collapse all" : "Expand all"}
        </button>
      </div>
      <ul className="flex flex-col">
        {sorted.map((p) => (
          <Row
            key={p.id}
            post={p}
            open={open.has(p.id)}
            onToggle={() => toggle(p.id)}
            reduced={reduced}
          />
        ))}
      </ul>
    </Card>
  );
}

export default DailyQuestionStack;
