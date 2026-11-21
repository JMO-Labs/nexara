/**
 * @file tests/unit/layout/CreateMenu.test.tsx
 * @brief Create dropdown lists the four create actions.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { CreateMenu } from "@/components/layout/CreateMenu";
import { useModals } from "@/stores/modals";

describe("CreateMenu", () => {
  it("opens and lists the four items", async () => {
    render(<CreateMenu />);
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    for (const n of ["New post", "New event", "Upload photos", "New list"])
      expect(screen.getByRole("menuitem", { name: n })).toBeInTheDocument();
  });

  it("New post opens the composer modal", async () => {
    const show = vi.fn();
    useModals.setState({ show } as never);
    render(<CreateMenu compact />);
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "New post" }));
    expect(show).toHaveBeenCalledWith("create-post");
  });
});
