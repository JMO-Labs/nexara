"use client";
/**
 * @file components/events/event-detail/ContributionSlots.tsx
 * @brief Contribution slot list with claim/unclaim buttons.
 */
import {
  useClaimContribution,
  useUnclaimContribution,
} from "@/hooks/useEvents";
import { useSession } from "@/stores/session";
import type { ContributionSlot } from "@/lib/api/events";

const BTN =
  "rounded-md border border-ink/20 px-2 py-0.5 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50";

/**
 * @brief Render slots for an event.
 * @param eventId owning event id
 * @param slots contribution slots
 * @return list element, or null when empty
 */
export function ContributionSlots({
  eventId,
  slots,
}: {
  eventId: string;
  slots: ContributionSlot[];
}) {
  const userId = useSession((s) => s.user?.id);
  const claim = useClaimContribution(eventId);
  const unclaim = useUnclaimContribution(eventId);
  if (slots.length === 0) return null;
  return (
    <div className="mt-4">
      <h3 className="mb-1.5 text-xs font-semibold tracking-wider text-muted">
        Contributions
      </h3>
      <ul className="flex flex-col gap-1">
        {slots.map((slot) => {
          const mine = !!userId && slot.claimed_by.includes(userId);
          const open = slot.quantity_claimed < slot.quantity_needed;
          return (
            <li
              key={slot.id ?? slot.title}
              className="flex items-center justify-between gap-2 rounded-lg border border-ink/15 px-2 py-1.5"
            >
              <span className="text-sm">{slot.title}</span>
              <span className="flex items-center gap-2">
                <span className="text-xs tabular-nums text-muted">
                  {slot.quantity_claimed} / {slot.quantity_needed}
                </span>
                {slot.id && mine ? (
                  <button
                    type="button"
                    className={BTN}
                    aria-label={`Unclaim ${slot.title}`}
                    disabled={unclaim.isPending}
                    onClick={() => unclaim.mutate(slot.id as string)}
                  >
                    Unclaim
                  </button>
                ) : slot.id && open ? (
                  <button
                    type="button"
                    className={BTN}
                    aria-label={`Claim ${slot.title}`}
                    disabled={claim.isPending}
                    onClick={() => claim.mutate(slot.id as string)}
                  >
                    Claim
                  </button>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
