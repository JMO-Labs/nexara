"use client";
/**
 * @file components/prompts/SuggestQuestionDialog.tsx
 * @brief Link-button + dialog for members to suggest a daily question.
 */
import * as React from "react";
import { Button, Modal, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api/errors";
import { suggestQuestion } from "@/lib/api/dailyQuestions";
import { useToasts } from "@/stores/toasts";

const MAX = 280;

/**
 * @brief "Suggest a question" trigger and dialog.
 * @return element
 */
export function SuggestQuestionDialog() {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const push = useToasts((s) => s.push);
  const content = text.trim();

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await suggestQuestion(content);
      push({
        variant: "success",
        message: "Thanks — an admin will review it",
      });
      setText("");
      setOpen(false);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 429
          ? "You can suggest 3 questions a day"
          : "Couldn't send your suggestion. Try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        className="min-h-11 self-start text-sm text-accent underline underline-offset-2"
        onClick={() => setOpen(true)}
      >
        Suggest a question
      </button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Suggest a question"
        description="An admin reviews suggestions before they are asked."
        footer={
          <Button
            className="min-h-11"
            onClick={submit}
            disabled={!content || busy}
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
        {error && (
          <p role="alert" className="mt-2 text-sm text-danger">
            {error}
          </p>
        )}
      </Modal>
    </>
  );
}

export default SuggestQuestionDialog;
