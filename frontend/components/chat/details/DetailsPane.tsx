"use client";
/**
 * @file components/chat/details/DetailsPane.tsx
 * @brief Loads conversation context and renders the person or group body.
 */
import { Skeleton } from "@/components/ui";
import { useChatContext } from "@/hooks/useChatContext";
import { GroupDetails } from "./GroupDetails";
import { PersonDetails } from "./PersonDetails";

/**
 * @param channelId active channel id
 * @return details content (loading, error or body)
 */
export function DetailsPane({ channelId }: { channelId: string }) {
  const q = useChatContext(channelId);
  if (q.isLoading) {
    return (
      <div data-testid="details-skeleton" className="flex flex-col gap-3">
        <Skeleton height={80} />
        <Skeleton height={48} />
      </div>
    );
  }
  if (q.isError || !q.data) {
    return <p className="text-sm text-muted">Details are not available.</p>;
  }
  return q.data.kind === "dm" ? (
    <PersonDetails ctx={q.data} />
  ) : (
    <GroupDetails ctx={q.data} />
  );
}
