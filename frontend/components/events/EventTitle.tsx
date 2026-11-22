/**
 * @file components/events/EventTitle.tsx
 * @brief Event title with a cake (birthday) or paw (pet) icon for
 *        calendar celebrations.
 */
import { Cake, PawPrint } from "lucide-react";
import type { EventItem } from "@/lib/api/events";
import { celebrationOf } from "@/lib/celebrations";

/** @brief Title text, prefixed with an icon for celebrations. */
export function EventTitle({ ev }: { ev: EventItem }) {
  const c = celebrationOf(ev);
  if (!c) return <>{ev.title}</>;
  const Icon = c.is_pet ? PawPrint : Cake;
  return (
    <>
      <Icon className="mr-1 inline size-3.5 align-[-2px]" aria-hidden />
      {ev.title}
    </>
  );
}
