/**
 * @file tests/unit/components/expenses/expenses.test.tsx
 * @brief Expenses API paths, money format, ExpenseForm, BalanceList, SettleDialog.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BalanceList } from "@/components/expenses/BalanceList";
import { ExpenseForm } from "@/components/expenses/ExpenseForm";
import { SettleDialog } from "@/components/expenses/SettleDialog";
import * as client from "@/lib/api/client";
import * as api from "@/lib/api/expenses";

vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: vi.fn().mockResolvedValue({}),
  apiPost: vi.fn().mockResolvedValue({}),
  apiPut: vi.fn().mockResolvedValue({}),
  apiPatch: vi.fn().mockResolvedValue({}),
  apiDelete: vi.fn().mockResolvedValue({}),
}));

const members = [
  { user_id: "a", name: "Ana" },
  { user_id: "b", name: "Bo" },
];
const transfer = {
  from_user_id: "b",
  from_name: "Bo",
  to_user_id: "a",
  to_name: "Ana",
  cents: 4000,
};

describe("expenses api paths", () => {
  beforeEach(() => vi.clearAllMocks());
  it("every call starts with /api/v1/expenses", async () => {
    await api.getCurrency();
    await api.setCurrency("EUR");
    await api.listLedgers({ event_id: "e1" });
    await api.getLedger("l1");
    await api.createLedger({ name: "x", member_ids: [] });
    await api.updateLedger("l1", { archived: true });
    await api.addLedgerMembers("l1", ["u"]);
    await api.removeLedgerMember("l1", "u");
    await api.addExpense("l1", {} as api.ExpenseInput);
    await api.deleteExpense("l1", "x1");
    await api.settle("l1", {} as api.SettleInput);
    await api.splitGift("i1");
    const calls = [
      ...vi.mocked(client.apiGet).mock.calls,
      ...vi.mocked(client.apiPost).mock.calls,
      ...vi.mocked(client.apiPut).mock.calls,
      ...vi.mocked(client.apiPatch).mock.calls,
      ...vi.mocked(client.apiDelete).mock.calls,
    ].map((c) => c[0]);
    expect(calls).toHaveLength(12);
    for (const p of calls) expect(p).toMatch(/^\/api\/v1\/expenses\//);
    expect(calls).toContain("/api/v1/expenses/ledgers?event_id=e1");
    expect(calls).toContain("/api/v1/expenses/ledgers/from-wishlist-item/i1");
  });
});

describe("formatCents", () => {
  it("formats with Intl currency", () => {
    expect(api.formatCents(1250, "USD", "en-US")).toBe("$12.50");
    expect(api.formatCents(4000, "EUR", "en-US")).toBe("€40.00");
  });
});

describe("ExpenseForm", () => {
  it("submits an equal split with decimal amount in cents", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <ExpenseForm
        members={members}
        currency="USD"
        meId="a"
        onSubmit={onSubmit}
      />,
    );
    expect(screen.getByLabelText("Amount")).toHaveAttribute(
      "inputmode",
      "decimal",
    );
    await userEvent.type(screen.getByLabelText("Amount"), "10.01");
    await userEvent.type(screen.getByLabelText("What was it for"), "Cabin");
    await userEvent.click(screen.getByRole("button", { name: "Add expense" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      payer_id: "a",
      amount_cents: 1001,
      description: "Cabin",
      split: "equal",
      split_among: ["a", "b"],
    });
  });

  it("blocks custom shares that do not add up", async () => {
    const onSubmit = vi.fn();
    render(
      <ExpenseForm
        members={members}
        currency="USD"
        meId="a"
        onSubmit={onSubmit}
      />,
    );
    await userEvent.type(screen.getByLabelText("Amount"), "10");
    await userEvent.type(screen.getByLabelText("What was it for"), "Cabin");
    await userEvent.click(
      screen.getByRole("radio", { name: "Custom amounts" }),
    );
    await userEvent.type(screen.getByLabelText("Share for Ana"), "6");
    await userEvent.type(screen.getByLabelText("Share for Bo"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Add expense" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/add up/);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe("BalanceList", () => {
  it("shows who owes whom and Settle only to the two parties", async () => {
    const onSettle = vi.fn();
    const { rerender } = render(
      <BalanceList
        transfers={[transfer]}
        balances={[]}
        currency="USD"
        meId="b"
        onSettle={onSettle}
      />,
    );
    expect(screen.getByText(/You owe/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Settle/ }));
    expect(onSettle).toHaveBeenCalledWith(transfer);
    rerender(
      <BalanceList
        transfers={[transfer]}
        balances={[]}
        currency="USD"
        meId="z"
        onSettle={onSettle}
      />,
    );
    expect(screen.queryByRole("button", { name: /Settle/ })).toBeNull();
    expect(screen.getByText(/Bo owes Ana/)).toBeInTheDocument();
  });

  it("says everyone is settled when empty", () => {
    render(
      <BalanceList
        transfers={[]}
        balances={[]}
        currency="USD"
        meId="a"
        onSettle={vi.fn()}
      />,
    );
    expect(screen.getByText("Everyone is settled up.")).toBeInTheDocument();
  });
});

describe("SettleDialog", () => {
  it("confirms the full suggested amount by default", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <SettleDialog
        transfer={transfer}
        currency="USD"
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /^Settle/ }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith(transfer, 4000));
  });
});
