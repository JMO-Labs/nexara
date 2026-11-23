/**
 * @file tests/unit/components/relations/relations.test.tsx
 * @brief Add dialog sends "<person> is my <kind>"; requests accept/decline.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const requestRelation = vi.fn().mockResolvedValue({});
const confirmRelation = vi.fn().mockResolvedValue({});
const removeRelation = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/api/relations", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/relations")>()),
  requestRelation: (...a: unknown[]) => requestRelation(...a),
  confirmRelation: (...a: unknown[]) => confirmRelation(...a),
  removeRelation: (...a: unknown[]) => removeRelation(...a),
  listRelationRequests: () =>
    Promise.resolve([
      {
        id: "r1",
        status: "pending",
        kind: "child",
        label: null,
        display: "child",
        direction: "incoming",
        person: { id: "u2", type: "user", name: "Dana", memorial: false },
      },
    ]),
}));
vi.mock("@/hooks/useMembersList", () => ({
  useMembersList: () => ({
    data: [
      { id: "me", display_name: "Me", username: "me" },
      { id: "u2", display_name: "Dana", username: "dana" },
    ],
  }),
}));
vi.mock("@/hooks/useHousehold", () => ({
  useVisibleHousehold: () => ({ data: [] }),
}));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: { user: { id: string } }) => unknown) =>
    sel({ user: { id: "me" } }),
}));

import { AddRelationDialog } from "@/components/relations/AddRelationDialog";
import { RelationRequests } from "@/components/relations/RelationRequests";

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );

describe("relations UI", () => {
  beforeEach(() => vi.clearAllMocks());

  it("add dialog needs a person, then posts the kind", async () => {
    const user = userEvent.setup();
    wrap(<AddRelationDialog open onClose={() => {}} />);
    expect(screen.getByText("They is my …")).toBeTruthy();
    expect(
      (
        screen.getByRole("button", {
          name: "Add",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    await user.click(screen.getByRole("combobox", { name: "Member" }));
    expect(screen.queryByRole("option", { name: "Me" })).toBeNull();
    await user.click(screen.getByRole("option", { name: "Dana" }));
    expect(screen.getByText("Dana is my …")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Send request" }));
    expect(requestRelation.mock.calls[0][0]).toEqual({
      to_user_id: "u2",
      kind: "parent",
    });
  });

  it("requests list accepts and declines", async () => {
    const user = userEvent.setup();
    wrap(<RelationRequests />);
    expect(
      await screen.findByText(/Dana says you're their parent/),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Accept Dana" }));
    expect(confirmRelation.mock.calls[0][0]).toBe("r1");
    await user.click(screen.getByRole("button", { name: "Decline Dana" }));
    expect(removeRelation.mock.calls[0][0]).toBe("r1");
  });
});
