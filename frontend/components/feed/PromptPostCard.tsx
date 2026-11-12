"use client";
/**
 * @file components/feed/PromptPostCard.tsx
 * @brief Card for prompt posts: live response count, interest hint, reply.
 */
import * as React from "react";
import { Flag, Sparkles } from "lucide-react";
import { Badge, Button, Card } from "@/components/ui";
import { usePromptResponses } from "@/hooks/usePromptResponses";
import type { PromptPost } from "@/lib/api/prompts";

export interface PromptPostCardProps {
  post: PromptPost;
  onReply?: (promptId: string) => void;
}

/**
 * @brief Prompt post card.
 * @param post the prompt post
 * @param onReply called with the prompt id when Reply is pressed
 * @return card element
 */
export const PromptPostCard: React.FC<PromptPostCardProps> = ({
  post,
  onReply,
}) => {
  const { data: responseData } = usePromptResponses(post.id);
  const displayCount = responseData?.response_count ?? post.response_count;
  const isInterestCapture = post.prompt.prompt_type === "interest_capture";

  return (
    <Card className="relative flex flex-col gap-4 border-l-4 border-accent p-4">
      {post.is_pinned && (
        <div
          data-testid="pinned-icon"
          className="absolute right-3 top-3 text-accent"
        >
          <Flag className="size-4" aria-label="Pinned" />
        </div>
      )}

      {post.subgroup_name && (
        <div>
          <Badge>{post.subgroup_name}</Badge>
        </div>
      )}

      <h3 className="text-lg font-semibold italic leading-snug">
        {post.prompt.title}
      </h3>

      {isInterestCapture && post.prompt.interest_capture_hint && (
        <p className="flex items-center gap-2 rounded-xl bg-bg p-2 text-xs italic">
          <Sparkles className="size-3.5 shrink-0" aria-hidden="true" />
          {post.prompt.interest_capture_hint}
        </p>
      )}

      <div className="flex items-center justify-between gap-2">
        <div role="status" aria-live="polite" aria-atomic="true">
          <Badge>
            {`${displayCount} ${displayCount === 1 ? "response" : "responses"}`}
          </Badge>
        </div>
        <Button size="sm" onClick={() => onReply?.(post.prompt.id)}>
          Reply
        </Button>
      </div>
    </Card>
  );
};

export default PromptPostCard;
