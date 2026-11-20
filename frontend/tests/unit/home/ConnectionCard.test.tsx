/**
 * @file tests/unit/home/ConnectionCard.test.tsx
 * @brief ConnectionCard: visible ink Message pill and glass Profile pill.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConnectionCard } from "@/components/home/ConnectionCard";
import type { HomePerson } from "@/lib/api/home";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync: vi.fn() }),
}));

const person = {
  user_id: "u1",
  display_name: "Tomás Reyes",
  shared_groups: [],
  shared_events_30d: 0,
} as unknown as HomePerson;

describe("ConnectionCard", () => {
  it("styles Message as an ink pill and Profile as a glass pill", () => {
    render(<ConnectionCard person={person} status="" />);
    const message = screen.getByRole("button", { name: "Message" });
    expect(message).toHaveClass("bg-surface-strong", "text-bg", "text-sm");
    const profile = screen.getByRole("button", { name: "Profile" });
    expect(profile).toHaveClass("glass-item", "text-sm");
  });
});
