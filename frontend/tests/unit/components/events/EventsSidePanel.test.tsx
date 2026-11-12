/**
 * @file tests/unit/components/events/EventsSidePanel.test.tsx
 * @brief Responsive layout classes: rail stacks below lg, sticky at lg.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventsSidePanel } from "@/components/events/events-page/EventsSidePanel";

vi.mock("@/components/events/EventRail", () => ({ EventRail: () => <div /> }));
vi.mock("@/components/events/EventCountdown", () => ({
  EventCountdown: () => <div />,
}));

describe("EventsSidePanel layout", () => {
  it("is static when stacked (390px) and sticky at lg (1280px)", () => {
    render(
      <EventsSidePanel
        nextEvent={null}
        railEvents={[]}
        selectedDay={null}
        selectedEventId={null}
        subgroupNames={new Map()}
        onSelectEvent={() => {}}
        onClearDay={() => {}}
      />,
    );
    const cls = screen.getByRole("complementary").className;
    expect(cls).toContain("lg:sticky");
    expect(cls).not.toMatch(/(^|\s)sticky/);
  });
});
