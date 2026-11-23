"use client";
/**
 * @file components/admin/CurrencySetting.tsx
 * @brief Admin general settings: community default currency for shared costs.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Panel } from "@/components/ui/page";
import { selectCls } from "@/components/wishlists/wizard/fields";
import { CURRENCIES, getCurrency, setCurrency } from "@/lib/api/expenses";
import { formatApiError } from "@/lib/api/errors";
import { useToasts } from "@/stores/toasts";

/** @return panel with a currency select (saves on change) */
export function CurrencySetting() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["expenses", "currency"],
    queryFn: getCurrency,
  });
  const save = useMutation({
    mutationFn: setCurrency,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["expenses", "currency"] });
      useToasts
        .getState()
        .push({ variant: "success", message: "Currency saved" });
    },
    onError: (e) =>
      useToasts
        .getState()
        .push({ variant: "danger", message: formatApiError(e) }),
  });
  const value = data?.currency ?? "USD";
  return (
    <Panel as="div" title="Shared costs">
      <div className="flex flex-wrap items-center justify-between gap-3 py-2">
        <div className="min-w-0">
          <label htmlFor="community-currency" className="text-sm font-medium">
            Community currency
          </label>
          <p className="mt-0.5 text-xs text-muted">
            New shared-cost ledgers start with this currency.
          </p>
        </div>
        <select
          id="community-currency"
          className={`${selectCls} w-32`}
          value={value}
          disabled={!data || save.isPending}
          onChange={(e) => save.mutate(e.target.value)}
        >
          {[...new Set([value, ...CURRENCIES])].map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
    </Panel>
  );
}
