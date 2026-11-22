/**
 * @file app/app/expenses/page.tsx
 * @brief Shared costs: my ledgers and a form to start a new one.
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Receipt } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button, EmptyState, Modal } from "@/components/ui";
import { PageHeader, Panel } from "@/components/ui/page";
import { LedgerForm } from "@/components/expenses/LedgerForm";
import { useFeature } from "@/hooks/useFeature";
import { listLedgers } from "@/lib/api/expenses";

export default function ExpensesRoute() {
  const on = useFeature("expenses");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { data = [], isLoading } = useQuery({
    queryKey: ["expenses", "ledgers", {}],
    queryFn: () => listLedgers(),
    enabled: on,
  });
  if (!on) return null;
  return (
    <div className="mx-auto flex w-full max-w-[800px] flex-col gap-5 pb-8">
      <PageHeader
        title="Shared costs"
        description="Keep track of who paid and who owes."
        actions={<Button onClick={() => setOpen(true)}>New ledger</Button>}
      />
      {!isLoading && data.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title="No shared costs yet"
          description="Start a ledger for a trip, a gift or a dinner."
        />
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {data.map((l) => (
            <li key={l.id}>
              <Panel as="div">
                <Link
                  href={`/app/expenses/${l.id}`}
                  className="flex min-h-11 flex-wrap items-center justify-between gap-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                >
                  <span className="font-semibold">{l.name}</span>
                  <span className="text-sm text-muted">
                    {l.member_count} people
                    {l.archived ? " · archived" : ""}
                  </span>
                </Link>
              </Panel>
            </li>
          ))}
        </ul>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="New ledger">
        <LedgerForm onCreated={(l) => router.push(`/app/expenses/${l.id}`)} />
      </Modal>
    </div>
  );
}
