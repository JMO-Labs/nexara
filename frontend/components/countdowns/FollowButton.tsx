"use client";
/**
 * @file components/countdowns/FollowButton.tsx
 * @brief Follow/Following toggle for a countdown.
 */
import { Button } from "@/components/ui";
import { useToggleFollow } from "@/hooks/useCountdowns";

/**
 * @brief Toggle button; the accessible name carries state and countdown.
 * @param id countdown id
 * @param title countdown title (accessible name)
 * @param following current state
 * @return button
 */
export function FollowButton({
  id,
  title,
  following,
}: {
  id: string;
  title: string;
  following: boolean;
}) {
  const m = useToggleFollow(id);
  return (
    <Button
      size="sm"
      variant={following ? "secondary" : "primary"}
      aria-label={`${following ? "Following" : "Follow"} ${title}`}
      disabled={m.isPending}
      onClick={() => m.mutate(!following)}
    >
      {following ? "Following" : "Follow"}
    </Button>
  );
}
