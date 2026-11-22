"use client";
/**
 * @file components/expenses/EventSharedCosts.tsx
 * @brief Event page block: my shared-cost ledgers for the event, or start one.
 */
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Receipt } from "lucide-react";
import { Button, Modal } from "@/components/ui";
import { useFeature } from "@/hooks/useFeature";
import { listLedgers } from "@/lib/api/expenses";
import { LedgerForm } from "./LedgerForm";

/** @brief Create form; mounted only while the modal is open (needs the router). */
function NewEventLedger({
  eventId,
  title,
}: {
  eventId: string;
  title: string;
}) {
  const router = useRouter();
  return (
    <LedgerForm
      eventId={eventId}
      defaultName={title}
      onCreated={(l) => router.push(`/app/expenses/${l.id}`)}
    />
  );
}

/**
 * @param eventId event id
 * @param title event title (default ledger name)
 * @return block, or null when shared expenses are off
 */
export function EventSharedCosts({
  eventId,
  title,
}: {
  eventId: string;
  title: string;
}) {
  const on = useFeature("expenses");
  const [open, setOpen] = useState(false);
  const { data = [] } = useQuery({
    queryKey: ["expenses", "ledgers", { event_id: eventId }],
    queryFn: () => listLedgers({ event_id: eventId }),
    enabled: on,
  });
  if (!on) return null;
  return (
    <section aria-label="Shared costs" className="mt-4 flex flex-col gap-2">
      <h3 className="text-sm font-semibold">Shared costs</h3>
      {data.map((l) => (
        <Link
          key={l.id}
          href={`/app/expenses/${l.id}`}
          className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-accent underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <Receipt className="size-4" aria-hidden /> {l.name}
        </Link>
      ))}
      <div>
        <Button size="sm" variant="glass" onClick={() => setOpen(true)}>
          Split costs for this event
        </Button>
      </div>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New shared costs"
      >
        {open && <NewEventLedger eventId={eventId} title={title} />}
      </Modal>
    </section>
  );
}
