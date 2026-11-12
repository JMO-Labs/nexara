/**
 * @file tests/unit/home/NewItemsPill.test.tsx
 * @brief NewItemsPill: count text, hidden at 0, click handler.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { NewItemsPill } from "@/components/home/NewItemsPill";

describe("NewItemsPill", () => {
  it("renders the count", () => {
    renderWithProviders(<NewItemsPill count={3} onClick={vi.fn()} />);
    expect(screen.getByRole("button", { name: "3 new" })).toBeInTheDocument();
  });

  it("renders no button at 0 but keeps the live region", () => {
    const { container } = renderWithProviders(
      <NewItemsPill count={0} onClick={vi.fn()} />,
    );
    expect(screen.queryByRole("button")).toBeNull();
    expect(container.querySelector("[aria-live='polite']")).not.toBeNull();
  });

  it("calls the handler on click", async () => {
    const onClick = vi.fn();
    renderWithProviders(<NewItemsPill count={2} onClick={onClick} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
