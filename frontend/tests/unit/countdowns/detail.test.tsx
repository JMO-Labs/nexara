/**
 * @file tests/unit/countdowns/detail.test.tsx
 * @brief Detail page: Delete only for the creator and community admins.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Suspense } from "react";

const st = { role: "member", id: "me" };
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/stores/session", () => ({
  useSession: (f: (s: unknown) => unknown) =>
    f({ user: { id: st.id, role: st.role } }),
}));
vi.mock("@/stores/confirmDialog", () => ({
  useConfirmDialog: (f: (s: unknown) => unknown) => f({ confirm: vi.fn() }),
}));
vi.mock("@/hooks/useCountdowns", () => ({
  useCountdown: () => ({ data: { id: "c1", author_id: "other" } }),
  useDeleteCountdown: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/components/countdowns/CountdownCard", () => ({
  CountdownCard: () => <div data-testid="card" />,
}));
vi.mock("@/components/countdowns/CountdownComposer", () => ({
  CountdownComposer: () => null,
}));
import Page from "@/app/app/countdowns/[id]/page";

const params = Object.assign(Promise.resolve({ id: "c1" }), {
  status: "fulfilled",
  value: { id: "c1" },
});

const show = (role: string) => {
  st.role = role;
  render(
    <Suspense>
      <Page params={params} />
    </Suspense>,
  );
  expect(screen.getByTestId("card")).toBeInTheDocument();
};

describe("countdown detail delete", () => {
  it("hidden for owner-role non-author", () => {
    show("owner");
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });
  it("shown for admin", () => {
    show("admin");
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });
});
