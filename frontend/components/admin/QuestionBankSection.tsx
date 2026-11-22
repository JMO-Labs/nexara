"use client";
/**
 * @file components/admin/QuestionBankSection.tsx
 * @brief Daily-question bank admin: pending suggestions (approve/reject) and
 *        an input to add an approved question.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Input } from "@/components/ui";
import {
  addQuestion,
  listQuestions,
  moderateQuestion,
} from "@/lib/api/dailyQuestions";

const KEY = ["admin", "daily-questions", "pending"] as const;

/**
 * @brief Question bank section for the Prompts admin tab.
 * @return section element
 */
export function QuestionBankSection() {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const pending = useQuery({
    queryKey: KEY,
    queryFn: () => listQuestions("pending"),
  });
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });
  const add = useMutation({
    mutationFn: addQuestion,
    onSuccess: () => setText(""),
  });
  const moderate = useMutation({
    mutationFn: (v: { id: string; action: "approve" | "reject" }) =>
      moderateQuestion(v.id, v.action),
    onSuccess: refresh,
  });
  const rows = pending.data ?? [];
  const content = text.trim();

  return (
    <section aria-labelledby="qbank-h" className="mt-8 flex flex-col gap-4">
      <h2 id="qbank-h" className="text-lg font-semibold">
        Daily question bank
      </h2>
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (content) add.mutate(content);
        }}
      >
        <div className="flex-1">
          <Input
            label="Add a question"
            value={text}
            maxLength={280}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
        <Button type="submit" className="min-h-11" disabled={!content}>
          Add
        </Button>
      </form>
      <h3 className="text-sm font-semibold">Pending suggestions</h3>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">No pending suggestions.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((r) => (
            <li
              key={r.id}
              className="glass-item flex flex-wrap items-center justify-between gap-2 rounded-[20px] p-3"
            >
              <span className="min-w-0 flex-1 text-sm">{r.text}</span>
              <span className="flex gap-2">
                <Button
                  size="sm"
                  className="min-h-11"
                  aria-label={`Approve: ${r.text}`}
                  onClick={() =>
                    moderate.mutate({ id: r.id, action: "approve" })
                  }
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  className="min-h-11"
                  aria-label={`Reject: ${r.text}`}
                  onClick={() =>
                    moderate.mutate({ id: r.id, action: "reject" })
                  }
                >
                  Reject
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default QuestionBankSection;
