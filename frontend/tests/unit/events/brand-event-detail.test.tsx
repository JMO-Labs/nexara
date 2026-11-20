/**
 * @file tests/unit/events/brand-event-detail.test.tsx
 * @brief Brand rules for the event detail: friendly date range (year dropped
 *        for the current year), glass RSVP pills, glass iCal action.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { format } from "date-fns";
import { formatRange } from "@/components/events/event-detail/formatRange";
import { ExportIcalButton } from "@/components/events/event-detail/ExportIcalButton";
import { RsvpInline } from "@/components/events/RsvpInline";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const year = new Date().getFullYear();

describe("formatRange", () => {
  it("drops the year for the current year and uses friendly times", () => {
    const d = new Date(year, 10, 21);
    expect(
      formatRange(`${year}-11-21T09:00:00`, `${year}-11-21T11:00:00`, false),
    ).toBe(`${format(d, "EEE, MMM d")} · 9 am to 11 am`);
  });

  it("keeps the year for other years", () => {
    expect(
      formatRange("2030-11-21T09:00:00", "2030-11-21T11:00:00", false),
    ).toContain(", 2030");
  });

  it("shows All day for all-day events", () => {
    expect(
      formatRange(`${year}-11-21T00:00:00`, `${year}-11-21T23:59:00`, true),
    ).toMatch(/· All day$/);
  });
});

describe("ExportIcalButton", () => {
  it("is a glass pill with ink text, not an accent link", () => {
    renderWithProviders(<ExportIcalButton eventId="e1" title="Picnic" />);
    const btn = screen.getByRole("button", { name: "exportIcal" });
    expect(btn.className).toContain("glass-btn");
    expect(btn.className).toContain("text-ink");
    expect(btn.className).not.toContain("text-accent");
  });
});

describe("RsvpInline brand", () => {
  it("inactive pills are glass items with no hard outline", () => {
    renderWithProviders(
      <RsvpInline
        eventId="e1"
        labels={{ attending: "Going", maybe: "Maybe" }}
        current="maybe"
        counts={{}}
      />,
    );
    const going = screen.getByRole("button", { name: "Going" });
    expect(going.className).toContain("glass-item");
    expect(going.className).toContain("min-h-10");
    expect(going.className).not.toContain("border-ink/30");
    const maybe = screen.getByRole("button", { name: "Maybe" });
    expect(maybe.className).toContain("bg-surface-strong");
  });
});
