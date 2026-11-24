"use client";
/**
 * @file components/countdowns/CountdownFeedCard.tsx
 * @brief Loads a post's countdown by id and renders its card.
 */
import { useCountdown } from "@/hooks/useCountdowns";
import { CountdownCard } from "./CountdownCard";

/**
 * @param id countdown id
 * @return card, or null while loading/unavailable
 */
export function CountdownFeedCard({ id }: { id: string }) {
  const { data } = useCountdown(id);
  return data ? <CountdownCard c={data} /> : null;
}
