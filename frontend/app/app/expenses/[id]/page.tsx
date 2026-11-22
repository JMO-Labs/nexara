/**
 * @file app/app/expenses/[id]/page.tsx
 * @brief One ledger: balances, settle, expenses and the add-expense form.
 */
"use client";

import { use, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Button, EmptyState, IconButton } from "@/components/ui";
import { PageHeader, Panel } from "@/components/ui/page";
import { BalanceList } from "@/components/expenses/BalanceList";
import { ExpenseForm } from "@/components/expenses/ExpenseForm";
import { SettleDialog } from "@/components/expenses/SettleDialog";
import { useFeature } from "@/hooks/useFeature";
import { ApiError, formatApiError } from "@/lib/api/errors";
import {
  addExpense,
  deleteExpense,
  formatCents,
  getLedger,
  settle,
  updateLedger,
  type Ledger,
  type Transfer,
} from "@/lib/api/expenses";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useSession } from "@/stores/session";
import { useToasts } from "@/stores/toasts";

export default function LedgerRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const on = useFeature("expenses");
  const me = useSession((s) => s.user?.id ?? "");
  const qc = useQueryClient();
  const confirm = useConfirmDialog((s) => s.confirm);
  const [paying, setPaying] = useState<Transfer | null>(null);
  const key = ["expenses", "ledger", id];
  const { data, error } = useQuery({
    queryKey: key,
    queryFn: () => getLedger(id),
    enabled: on,
    retry: false,
  });
  const put = (l: Ledger) => {
    qc.setQueryData(key, l);
    void qc.invalidateQueries({ queryKey: ["expenses", "ledgers"] });
  };
  const fail = (e: unknown) =>
    useToasts
      .getState()
      .push({ variant: "danger", message: formatApiError(e) });
  const archive = useMutation({
    mutationFn: (archived: boolean) => updateLedger(id, { archived }),
    onSuccess: put,
    onError: fail,
  });
  const del = useMutation({
    mutationFn: (eid: string) => deleteExpense(id, eid),
    onSuccess: put,
    onError: fail,
  });
  if (!on) return null;
  if (error instanceof ApiError && error.status === 404)
    return (
      <EmptyState
        title="Ledger not found"
        description="It may have been removed, or you are not part of it."
      />
    );
  if (!data) return null;
  const { currency } = data;
  return (
    <div className="mx-auto flex w-full max-w-[800px] flex-col gap-5 pb-8">
      <PageHeader
        title={data.name}
        description={`${data.members.map((m) => m.name).join(", ")} · ${currency}`}
        back={{ href: "/app/expenses", label: "Shared costs" }}
        actions={
          data.can_manage ? (
            <Button
              variant="glass"
              onClick={() => archive.mutate(!data.archived)}
            >
              {data.archived ? "Reopen" : "Archive"}
            </Button>
          ) : undefined
        }
      />
      <Panel title="Balances">
        <BalanceList
          transfers={data.transfers}
          balances={data.balances}
          currency={currency}
          meId={me}
          onSettle={setPaying}
        />
      </Panel>
      {!data.archived && (
        <Panel title="Add an expense">
          <ExpenseForm
            members={data.members}
            currency={currency}
            meId={me}
            onSubmit={async (b) => put(await addExpense(id, b))}
          />
        </Panel>
      )}
      <Panel title="Expenses">
        {data.expenses.length === 0 ? (
          <p className="text-sm text-muted">Nothing added yet.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {data.expenses.map((e) => (
              <li key={e.id} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium">{e.description}</p>
                  <p className="text-xs text-muted">
                    {e.payer_name} paid {formatCents(e.amount_cents, currency)}{" "}
                    on {e.spent_on}
                  </p>
                </div>
                <IconButton
                  variant="ghost"
                  size="sm"
                  aria-label={`Delete ${e.description}`}
                  onClick={async () => {
                    if (
                      await confirm({
                        title: `Delete ${e.description}?`,
                        message: "Balances will be recalculated.",
                        confirmLabel: "Delete",
                        tone: "danger",
                      })
                    )
                      del.mutate(e.id);
                  }}
                >
                  <Trash2 className="size-4" aria-hidden />
                </IconButton>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <SettleDialog
        key={
          paying
            ? `${paying.from_user_id}-${paying.to_user_id}-${paying.cents}`
            : "none"
        }
        transfer={paying}
        currency={currency}
        onClose={() => setPaying(null)}
        onConfirm={async (t, cents) => {
          put(
            await settle(id, {
              from_user_id: t.from_user_id,
              to_user_id: t.to_user_id,
              amount_cents: cents,
            }),
          );
          setPaying(null);
        }}
      />
    </div>
  );
}
