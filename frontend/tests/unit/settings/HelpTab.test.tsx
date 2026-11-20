/**
 * @file tests/unit/settings/HelpTab.test.tsx
 * @brief Settings Help tab opens the keyboard shortcuts modal.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HelpTab } from "@/components/settings/HelpTab";
import { useModals } from "@/stores/modals";

describe("HelpTab", () => {
  beforeEach(() => {
    useModals.setState({ keyboardShortcutsOpen: false });
  });

  it("renders the heading and opens keyboard shortcuts", async () => {
    render(<HelpTab />);
    expect(
      screen.getByRole("heading", { name: "Help", level: 2 }),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Keyboard shortcuts" }),
    );
    expect(useModals.getState().keyboardShortcutsOpen).toBe(true);
  });
});
