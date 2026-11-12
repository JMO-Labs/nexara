"use client";
/**
 * @file app/app/prompts/[id]/page.tsx
 * @brief Responses to a fired prompt, linked from the prompt card.
 */
import { use } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui";
import { PromptResponsesList } from "@/components/prompts/PromptResponsesList";
import { usePromptPost } from "@/hooks/usePrompts";

export default function PromptResponsesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: promptPost } = usePromptPost(id);

  return (
    <div className="mx-auto flex w-full max-w-180 flex-col gap-4">
      <div>
        <Button asChild variant="ghost" size="sm" className="min-h-11">
          <Link href="/app">
            <ChevronLeft className="size-4" aria-hidden="true" />
            Back to feed
          </Link>
        </Button>
      </div>
      <h1 className="text-xl font-semibold">
        {promptPost?.prompt.title ?? "Responses"}
      </h1>
      <PromptResponsesList promptPostId={id} />
    </div>
  );
}
