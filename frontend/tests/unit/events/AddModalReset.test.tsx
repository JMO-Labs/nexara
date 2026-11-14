/**
 * @file tests/unit/events/AddModalReset.test.tsx
 * @brief AddModal resets its form to `initial` each time it is reopened.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AddModal } from "@/components/events/subscriptions/AddModal";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));

const initial = {
  title: "Work",
  source_url: "https://e.com/a.ics",
  sync_interval_minutes: 60,
};

const ui = (open: boolean) => (
  <AddModal
    open={open}
    onClose={vi.fn()}
    onSubmit={vi.fn()}
    isLoading={false}
    initial={initial}
  />
);

const titleInput = () =>
  screen.getByLabelText(
    "components.calendar.subscriptions.title",
  ) as HTMLInputElement;

describe("AddModal reset", () => {
  it("restores initial values when reopened after edits", () => {
    const { rerender } = render(ui(true));
    fireEvent.change(titleInput(), { target: { value: "Edited" } });
    expect(titleInput().value).toBe("Edited");
    rerender(ui(false));
    rerender(ui(true));
    expect(titleInput().value).toBe("Work");
  });

  it("keeps edits while staying open across rerenders", () => {
    const { rerender } = render(ui(true));
    fireEvent.change(titleInput(), { target: { value: "Edited" } });
    rerender(ui(true));
    expect(titleInput().value).toBe("Edited");
  });
});
