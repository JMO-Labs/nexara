"use client";
/**
 * @file components/countdowns/FollowButton.tsx
 * @brief Follow/Following toggle for a countdown.
 */
import { Button } from "@/components/ui";
import { useToggleFollow } from "@/hooks/useCountdowns";

/**
 * @brief Toggle button (aria-pressed).
 * @param id countdown id
 * @param following current state
 * @return button
 */
export function FollowButton({
  id,
  following,
}: {
  id: string;
  following: boolean;
}) {
  const m = useToggleFollow(id);
  return (
    <Button
      size="sm"
      variant={following ? "secondary" : "primary"}
      aria-pressed={following}
      disabled={m.isPending}
      onClick={() => m.mutate(!following)}
    >
      {following ? "Following" : "Follow"}
    </Button>
  );
}
