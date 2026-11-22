/**
 * @file tests/unit/components/capsules/capsules.test.tsx
 * @brief Sealed card/view never show content; composer blocks past dates.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const createCapsule = vi.fn();
vi.mock("@/lib/api/capsules", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/capsules")>()),
  createCapsule: (...a: unknown[]) => createCapsule(...a),
}));
vi.mock("@/hooks/useMembersList", () => ({
  useMembersList: () => ({
    data: [{ id: "u2", display_name: "Maya", username: "maya" }],
  }),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [] }),
}));
vi.mock("@/hooks/useHousehold", () => ({
  useVisibleHousehold: () => ({ data: [] }),
}));

import { SealedCard } from "@/components/capsules/SealedCard";
import { CapsuleView } from "@/components/capsules/CapsuleView";
import {
  CapsuleComposer,
  tomorrow,
} from "@/components/capsules/CapsuleComposer";

const sealed = {
  id: "c1",
  title: "For Maya",
  author: { id: "u1", display_name: "Ruth" },
  open_at: "2034-05-01T12:00:00Z",
  recipients_summary: "1 people",
};

describe("capsules", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sealed card shows date, sender, lock and no body", () => {
    const { container } = render(
      <SealedCard capsule={{ ...sealed, body: "secret words" } as never} />,
    );
    expect(
      screen.getByText(/Opens May 1, 2034 · from Ruth/),
    ).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull();
    expect(container.textContent).not.toContain("secret words");
  });

  it("sealed view renders a placeholder, not content", () => {
    render(<CapsuleView capsule={sealed} mine={false} />);
    expect(screen.getByRole("status")).toHaveTextContent(/sealed/i);
  });

  it("composer blocks a date before tomorrow", async () => {
    const user = userEvent.setup();
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <CapsuleComposer open onClose={() => {}} />
      </QueryClientProvider>,
    );
    await user.type(screen.getByLabelText("Title"), "Hi");
    const d = new Date();
    const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const input = screen.getByLabelText(/Opens on/) as HTMLInputElement;
    expect(input.min).toBe(tomorrow());
    await user.type(input, today);
    await user.click(screen.getByRole("button", { name: "Seal capsule" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/tomorrow/);
    expect(createCapsule).not.toHaveBeenCalled();
  });
});
