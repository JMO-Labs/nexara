"use client";
/**
 * @file components/countdowns/CountdownFeedCard.tsx
 * @brief Loads a post's countdown by id and renders its card, with a
 *        skeleton while loading and a placeholder when unavailable.
 */
import { Card, Skeleton } from "@/components/ui";
import { useCountdown } from "@/hooks/useCountdowns";
import { CountdownCard } from "./CountdownCard";

/**
 * @param id countdown id
 * @param authorName post author's display name
 * @return card with author line, skeleton or unavailable placeholder
 */
export function CountdownFeedCard({
  id,
  authorName,
}: {
  id: string;
  authorName: string;
}) {
  const { data, isError } = useCountdown(id);
  if (data)
    return (
      <div className="flex flex-col gap-1.5">
        <p className="px-1 text-sm opacity-80">
          {authorName} started a countdown
        </p>
        <CountdownCard c={data} />
      </div>
    );
  if (isError)
    return (
      <Card className="p-4 text-sm" data-testid="countdown-unavailable">
        Countdown unavailable
      </Card>
    );
  return (
    <Card className="p-4" aria-busy="true" data-testid="countdown-loading">
      <Skeleton height={120} />
    </Card>
  );
}
