"use client";
/**
 * @file components/stories/AskStoryDialog.tsx
 * @brief "Ask for a story" button + dialog with ideas from the question bank.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Mic } from "lucide-react";
import { Button, Modal, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api/errors";
import { askStory, storyQuestions } from "@/lib/api/stories";
import { useToasts } from "@/stores/toasts";

const MAX = 280;

/**
 * @brief Pick `n` random ideas from the bank (stable per dialog open).
 * @param bank all suggested questions
 * @param n how many
 * @return shuffled sample
 */
export const sample = (bank: string[], n: number) =>
  [...bank].sort(() => Math.random() - 0.5).slice(0, n);

/**
 * @param userId member to ask
 * @param name their first name
 * @return trigger button and dialog
 */
export function AskStoryDialog({
  userId,
  name,
}: {
  userId: string;
  name: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const push = useToasts((s) => s.push);
  const bank = useQuery({
    queryKey: ["story-questions"],
    queryFn: storyQuestions,
    enabled: open,
    staleTime: Infinity,
  });
  const ideas = React.useMemo(
    () => sample(bank.data ?? [], 4),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bank.data, open],
  );
  const question = text.trim();

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      await askStory(userId, question);
      push({ variant: "success", message: `Question sent to ${name}` });
      setText("");
      setOpen(false);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 422
          ? "You already have several open questions for this person."
          : "Couldn't send your question. Try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        variant="secondary"
        className="min-h-11"
        onClick={() => setOpen(true)}
      >
        <Mic className="size-4" aria-hidden /> Ask {name} for a story
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={`Ask ${name} for a story`}
        description="They can answer with a voice recording or text, or pass quietly."
        footer={
          <Button
            className="min-h-11"
            onClick={send}
            disabled={!question || busy}
          >
            Send
          </Button>
        }
      >
        <Textarea
          label="Your question"
          value={text}
          maxLength={MAX}
          rows={3}
          onChange={(e) => setText(e.target.value)}
        />
        <p className="mt-1 text-xs text-muted" aria-live="polite">
          {text.length}/{MAX}
        </p>
        {ideas.length > 0 && (
          <div className="mt-3">
            <p className="mb-1 text-sm text-muted">Need an idea?</p>
            <ul className="flex flex-col gap-1">
              {ideas.map((q) => (
                <li key={q}>
                  <button
                    type="button"
                    onClick={() => setText(q)}
                    className="min-h-11 w-full rounded-xl px-3 py-2 text-left text-sm text-ink hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {error && (
          <p role="alert" className="mt-2 text-sm text-danger">
            {error}
          </p>
        )}
      </Modal>
    </>
  );
}

export default AskStoryDialog;
