"use client";
/**
 * @file components/feed/PromptBadges.tsx
 * @brief Prompt markers for feed posts: "Prompt summary" badge and
 *        "Reply to a prompt" link. Renders nothing for normal posts.
 */
import * as React from "react";
import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui";

export interface PromptBadgesProps {
  isPromptSummary?: boolean;
  replyToPromptId?: string | null;
}

/**
 * @brief Inner renderer; only mounted when a marker is needed so normal
 *        posts never require an intl provider.
 * @param isPromptSummary post is a prompt summary
 * @param replyToPromptId prompt id the post replies to
 * @return badge/link row
 */
function PromptBadgesInner({
  isPromptSummary,
  replyToPromptId,
}: PromptBadgesProps) {
  const t = useTranslations("feed.promptBadges");
  return (
    <div className="flex flex-wrap items-center gap-2">
      {isPromptSummary ? <Badge tone="accent">{t("summary")}</Badge> : null}
      {replyToPromptId ? (
        <Link
          href={`/app/prompts/${encodeURIComponent(replyToPromptId)}`}
          onClick={(e) => e.stopPropagation()}
          className="rounded-full outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <Badge tone="accent">
            <MessageCircle className="size-3" aria-hidden="true" />
            {t("replyToPrompt")}
          </Badge>
        </Link>
      ) : null}
    </div>
  );
}

/**
 * @brief Prompt markers for a post.
 * @param isPromptSummary post is a prompt summary
 * @param replyToPromptId prompt id the post replies to
 * @return markers or null
 */
export function PromptBadges(props: PromptBadgesProps) {
  if (!props.isPromptSummary && !props.replyToPromptId) return null;
  return <PromptBadgesInner {...props} />;
}

export default PromptBadges;
