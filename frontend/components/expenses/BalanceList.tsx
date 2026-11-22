"use client";
/**
 * @file components/expenses/BalanceList.tsx
 * @brief Who owes whom ("Maya owes Ruth $40") with a Settle button for the
 *        two people involved, plus each member's net balance.
 */
import { Button } from "@/components/ui";
import { formatCents, type Balance, type Transfer } from "@/lib/api/expenses";

/**
 * @brief Suggested payments and net balances.
 * @param transfers simplified payments
 * @param balances net per member (positive = owed)
 * @param currency ledger currency
 * @param meId signed-in user id
 * @param onSettle open the settle dialog for a transfer
 * @return section
 */
export function BalanceList({
  transfers,
  balances,
  currency,
  meId,
  onSettle,
}: {
  transfers: Transfer[];
  balances: Balance[];
  currency: string;
  meId: string;
  onSettle: (t: Transfer) => void;
}) {
  if (transfers.length === 0)
    return <p className="text-sm text-muted">Everyone is settled up.</p>;
  return (
    <div className="flex flex-col gap-4">
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {transfers.map((t) => (
          <li
            key={`${t.from_user_id}-${t.to_user_id}`}
            className="flex flex-wrap items-center justify-between gap-2"
          >
            <span>
              {t.from_user_id === meId ? "You" : t.from_name}{" "}
              {t.from_user_id === meId ? "owe" : "owes"}{" "}
              {t.to_user_id === meId ? "you" : t.to_name}{" "}
              <strong>{formatCents(t.cents, currency)}</strong>
            </span>
            {(t.from_user_id === meId || t.to_user_id === meId) && (
              <Button
                size="sm"
                variant="glass"
                onClick={() => onSettle(t)}
                aria-label={`Settle ${t.from_name} to ${t.to_name}`}
              >
                Settle
              </Button>
            )}
          </li>
        ))}
      </ul>
      <ul
        aria-label="Net balances"
        className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1 p-0 text-sm text-muted"
      >
        {balances.map((b) => (
          <li key={b.user_id}>
            {b.name}: {b.cents > 0 ? "+" : ""}
            {formatCents(b.cents, currency)}
          </li>
        ))}
      </ul>
    </div>
  );
}
