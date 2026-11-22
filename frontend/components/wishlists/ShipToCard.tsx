"use client";
/**
 * @file components/wishlists/ShipToCard.tsx
 * @brief Shipping address on a wishlist, with a copy button for checkout.
 */
import { Copy, MapPin } from "lucide-react";
import { IconButton } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import type { ShipTo } from "@/lib/api/wishlists";

/** @brief "Ship to" block; explains when the person stopped sharing. */
export function ShipToCard({ ship }: { ship: ShipTo }) {
  const push = useToasts((s) => s.push);
  const who = ship.name ? `Ship to ${ship.name}` : "Ship to";
  if (!ship.address)
    return (
      <p className="flex items-center gap-2 text-sm text-muted">
        <MapPin className="size-4" aria-hidden />
        {ship.name}&apos;s address isn&apos;t shared, so ask them where to send
        gifts.
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
              className="underline-offset-2 hover:underline"
              href={`/app/events?event=${encodeURIComponent(ship.event_id)}`}
            >
              {ship.name}
            </a>
          ) : (
            who
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
