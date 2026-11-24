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
 * @return card, skeleton or unavailable placeholder
 */
export function CountdownFeedCard({ id }: { id: string }) {
  const { data, isError } = useCountdown(id);
  if (data) return <CountdownCard c={data} />;
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
