"use client";
/**
 * @file app/app/prompts/[id]/page.tsx
 * @brief Responses to a fired prompt, linked from the prompt card.
 */
import { use } from "react";
import { PageHeader, Panel } from "@/components/ui/page";
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
    <div className="mx-auto flex w-full max-w-3xl flex-col">
      <PageHeader
        title={promptPost?.prompt.title ?? "Responses"}
        back={{ href: "/app", label: "Back to feed" }}
      />
      <Panel>
        <PromptResponsesList promptPostId={id} />
      </Panel>
    </div>
  );
}
