"use client";
/**
 * @file components/home/FavoriteButton.tsx
 * @brief Star toggle that pins a person to the home people strip.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { useHomePeople } from "@/hooks/useHomePeople";
import { setFavorite } from "@/lib/api/home";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

/**
 * @brief Pin/unpin star.
 * @param userId person
 * @param name display name for the label
 * @param className extra classes
 * @return toggle button
 */
export function FavoriteButton({
  userId,
  name,
  className,
}: {
  userId: string;
  name: string;
  className?: string;
}) {
  const qc = useQueryClient();
  const on =
    useHomePeople().data?.items.some(
      (p) => p.user_id === userId && p.favorite,
    ) ?? false;
  const toggle = useMutation({
    mutationFn: () => setFavorite(userId, !on),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.home.people() }),
  });
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={on ? `Unpin ${name}` : `Pin ${name} to Home`}
      title={on ? "Pinned to Home" : "Pin to Home"}
      disabled={toggle.isPending}
      onClick={() => toggle.mutate()}
      className={cn(
        "glass-item grid size-9 shrink-0 place-items-center rounded-full outline-none focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-60",
        className,
      )}
    >
      <Star
        aria-hidden
        className={cn(
          "size-4",
          on ? "fill-amber-400 text-amber-400" : "text-muted",
        )}
      />
    </button>
  );
}
