"use client";
/**
 * @file components/wishlists/ShipToCard.tsx
 * @brief Shipping address on a wishlist, with a copy button for checkout.
 *        Event addresses link to the event.
 */
import { Copy, MapPin } from "lucide-react";
import { IconButton } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import type { ShipTo } from "@/lib/api/wishlists";

/** @brief Why there is no address to show. */
function missing(ship: ShipTo): string {
  if (ship.event_id) return `${ship.name} has no location yet.`;
  if (ship.user_id)
    return `${ship.name}'s address isn't shared, so ask them where to send gifts.`;
  return "Ask the list owner where to send gifts.";
}

/** @brief "Ship to" block. */
export function ShipToCard({ ship }: { ship: ShipTo }) {
  const push = useToasts((s) => s.push);
  if (!ship.address)
    return (
      <p className="flex items-center gap-2 text-sm text-muted">
        <MapPin className="size-4 shrink-0" aria-hidden />
        {missing(ship)}
      </p>
    );
  const copy = () =>
    navigator.clipboard
      .writeText(ship.address ?? "")
      .then(() => push({ variant: "success", message: "Address copied" }))
      .catch(() => push({ variant: "danger", message: "Couldn't copy" }));
  return (
    <div className="glass-item flex max-w-md items-start gap-3 rounded-[20px] p-3">
      <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1 text-sm">
        <p className="font-medium">
          {ship.event_id ? (
            <a
              className="underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-accent"
              href={`/app/events?event=${encodeURIComponent(ship.event_id)}`}
            >
              {ship.name}
            </a>
          ) : ship.name ? (
            `Ship to ${ship.name}`
          ) : (
            "Ship to"
          )}
        </p>
        <p className="whitespace-pre-line text-muted">{ship.address}</p>
      </div>
      <IconButton
        variant="ghost"
        size="sm"
        aria-label="Copy shipping address"
        onClick={copy}
      >
        <Copy className="size-4" aria-hidden />
      </IconButton>
    </div>
  );
}
