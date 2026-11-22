"use client";
/**
 * @file components/prompts/DailyQuestionCard.tsx
 * @brief Daily question card: question, inline answer composer, and answers
 *        that stay hidden (count only) until the viewer answers.
 */
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Lock, MessageCircleQuestion } from "lucide-react";
import { Button, Card, Textarea } from "@/components/ui";
import { PromptResponsesList } from "@/components/prompts/PromptResponsesList";
import { SuggestQuestionDialog } from "@/components/prompts/SuggestQuestionDialog";
import { useFeature } from "@/hooks/useFeature";
import { useCreatePost } from "@/hooks/usePosts";
import { useInfinitePromptResponses } from "@/hooks/usePromptResponses";
import { qk } from "@/lib/query-keys";
import type { PromptPost } from "@/lib/api/prompts";

/**
 * @brief Card for a daily_question prompt post.
 * @param post the active prompt post
 * @return card element, or null when the feature is off
 */
export function DailyQuestionCard({ post }: { post: PromptPost }) {
  const on = useFeature("daily_question");
  const qc = useQueryClient();
  const [text, setText] = React.useState("");
  const create = useCreatePost();
  const q = useInfinitePromptResponses(post.id);
  if (!on) return null;

  const first = q.data?.pages[0];
  const locked = first?.locked === true;
  const answered = first?.answered === true;
  const count = locked ? (first?.count ?? 0) : post.response_count;
  const content = text.trim();
  const submit = () =>
    create.mutate(
      { content, reply_to_prompt_id: post.id },
      {
        onSuccess: () => {
          setText("");
          qc.invalidateQueries({ queryKey: qk.feed.promptResponses(post.id) });
        },
      },
    );

  return (
    <Card
      role="article"
      aria-label={`Daily question: ${post.prompt.body}`}
      className="flex flex-col gap-3 border-l-4 border-accent p-4"
    >
      <p className="flex items-center gap-2 text-sm font-medium text-muted">
        <MessageCircleQuestion className="size-4" aria-hidden="true" />
        Question of the day
      </p>
      <h3 className="text-lg leading-snug font-semibold">{post.prompt.body}</h3>
      {locked && (
        <p className="flex items-center gap-2 text-sm text-muted">
          <Lock className="size-4 shrink-0" aria-hidden="true" />
          <span>
            Answer to see what everyone said ·{" "}
            {`${count} ${count === 1 ? "answer" : "answers"}`}
          </span>
        </p>
      )}
      {answered ? (
        <p className="flex items-center gap-2 text-sm text-muted">
          <Check className="size-4 shrink-0" aria-hidden="true" />
          <span>
            You answered · {`${count} ${count === 1 ? "answer" : "answers"}`}
          </span>
        </p>
      ) : (
        <>
          <Textarea
            label="Your answer"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
          />
          <Button
            className="min-h-11 self-end"
            onClick={submit}
            disabled={!content || create.isPending}
          >
            Answer
          </Button>
        </>
      )}
      {first && !locked && (
        <PromptResponsesList promptPostId={post.id} searchable={false} />
      )}
      <SuggestQuestionDialog />
    </Card>
  );
}

export default DailyQuestionCard;
