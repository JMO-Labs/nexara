/**
 * @file components/capsules/SealedCard.tsx
 * @brief Sealed capsule card: lock, title, open date and sender. Never
 *        renders content (the API does not send it either).
 */
import Link from "next/link";
import { Lock } from "lucide-react";
import type { CapsuleSealed } from "@/lib/api/capsules";

/**
 * @param date ISO timestamp
 * @return e.g. "May 1, 2034"
 */
export const fmtDate = (date: string) =>
  new Date(date).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

/**
 * @param capsule sealed capsule
 * @return link card
 */
export function SealedCard({ capsule }: { capsule: CapsuleSealed }) {
  return (
    <Link
      href={`/app/capsules/${capsule.id}`}
      className="glass-item focus-visible:outline-accent flex items-center gap-3 rounded-2xl p-4 focus-visible:outline-2"
    >
      <Lock aria-hidden className="text-muted size-5 shrink-0" />
      <span className="flex min-w-0 flex-col">
        <span className="truncate font-semibold">{capsule.title}</span>
        <span className="text-muted text-sm">
          Opens {fmtDate(capsule.open_at)} · from {capsule.author.display_name}
        </span>
      </span>
    </Link>
  );
}
