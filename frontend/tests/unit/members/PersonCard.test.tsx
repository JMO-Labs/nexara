/**
 * @file tests/unit/members/PersonCard.test.tsx
 * @brief PersonCard: ink Message and glass Profile icon circles, single avatar ring.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PersonCard } from "@/components/members/PersonCard";
import type { DirectoryPerson } from "@/lib/api/users";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

const person = {
  user_id: "u1",
  display_name: "Tomás Reyes",
  username: "tomas",
  avatar_url: null,
  online: false,
  primary_group_id: null,
  shared_groups: [],
} as unknown as DirectoryPerson;

describe("PersonCard", () => {
  it("renders Message as an ink icon button and Profile as a glass button", () => {
    render(<PersonCard person={person} />);
    expect(
      screen.getByRole("button", { name: "Message Tomás Reyes" }),
    ).toHaveClass("bg-surface-strong", "text-bg");
    expect(
      screen.getByRole("button", { name: "View Tomás Reyes's profile" }),
    ).toHaveClass("glass-item");
  });

  it("uses a single avatar ring (no double box-shadow rings)", () => {
    const { container } = render(<PersonCard person={person} />);
    expect(container.innerHTML).not.toContain("0_0_0_4px");
  });
});
