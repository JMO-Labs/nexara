/**
 * @file tests/unit/events/RsvpInline.test.tsx
 * @brief RSVP option clicks call the (mocked) API and reflect selected state.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { RsvpInline } from "@/components/events/RsvpInline";
import { rsvpEvent, unrsvpEvent } from "@/lib/api/events";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/api/events", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/events")>()),
  rsvpEvent: vi.fn(),
  unrsvpEvent: vi.fn(),
}));

describe("RsvpInline", () => {
  beforeEach(() => {
    vi.mocked(rsvpEvent).mockReset().mockResolvedValue({} as never);
    vi.mocked(unrsvpEvent).mockReset().mockResolvedValue(undefined as never);
  });

  it("renders default options and marks the current one pressed", () => {
    renderWithProviders(<RsvpInline eventId="e1" current="maybe" />);
    expect(screen.getByRole("button", { name: "Maybe" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Going" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("clicking an option calls the RSVP API with its status", async () => {
    renderWithProviders(<RsvpInline eventId="e1" current={null} />);
    fireEvent.click(screen.getByRole("button", { name: "Going" }));
    await waitFor(() =>
      expect(rsvpEvent).toHaveBeenCalledWith("e1", "attending"),
    );
  });

  it("clicking the selected option removes the RSVP", async () => {
    renderWithProviders(<RsvpInline eventId="e1" current="attending" />);
    fireEvent.click(screen.getByRole("button", { name: "Going" }));
    await waitFor(() => expect(unrsvpEvent).toHaveBeenCalledWith("e1"));
  });

  it("uses custom labels and shows counts", () => {
    renderWithProviders(
      <RsvpInline
        eventId="e1"
        labels={{ yes: "Count me in" }}
        counts={{ yes: 4 }}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Count me in · 4" }),
    ).toBeInTheDocument();
  });
});
