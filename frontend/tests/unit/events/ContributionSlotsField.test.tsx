/**
 * @file tests/unit/events/ContributionSlotsField.test.tsx
 * @brief Tests for ContributionSlotsField and its wiring in EventCreateModal.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ContributionSlotsField } from "@/components/events/event-form/ContributionSlotsField";
import { EventCreateModal } from "@/components/events/EventCreateModal";
import type { ContributionSlot, EventItem } from "@/lib/api/events";

const createMutate = vi.fn().mockResolvedValue({});
const updateMutate = vi.fn().mockResolvedValue({});
vi.mock("@/hooks/useEvents", () => ({
  useCreateEvent: () => ({ mutateAsync: createMutate, isPending: false }),
  useUpdateEvent: () => ({ mutateAsync: updateMutate, isPending: false }),
}));
vi.mock("@/hooks/useCalendars", () => ({ useCalendars: () => ({ data: [] }) }));
vi.mock("@/components/events/event-form/LocationField", () => ({
  LocationField: () => null,
}));

const slot = (over: Partial<ContributionSlot> = {}): ContributionSlot => ({
  id: "s1",
  title: "Cake",
  quantity_needed: 2,
  quantity_claimed: 1,
  claimed_by: ["u1"],
  ...over,
});

function Harness({ initial = [] as ContributionSlot[] }) {
  const [v, setV] = React.useState(initial);
  return (
    <>
      <ContributionSlotsField value={v} onChange={setV} />
      <output data-testid="out">{JSON.stringify(v)}</output>
    </>
  );
}
const out = () => JSON.parse(screen.getByTestId("out").textContent!);

describe("ContributionSlotsField", () => {
  it("adds an empty slot with quantity 1", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "Add slot" }));
    expect(out()).toEqual([
      {
        id: null,
        title: "",
        quantity_needed: 1,
        quantity_claimed: 0,
        claimed_by: [],
      },
    ]);
    expect(screen.getByLabelText("Slot 1 title")).toBeInTheDocument();
  });

  it("edits title and quantity", () => {
    render(<Harness initial={[slot()]} />);
    fireEvent.change(screen.getByLabelText("Slot 1 title"), {
      target: { value: "Pie" },
    });
    fireEvent.change(screen.getByLabelText("Slot 1 quantity needed"), {
      target: { value: "5" },
    });
    expect(out()[0]).toMatchObject({
      id: "s1",
      title: "Pie",
      quantity_needed: 5,
    });
  });

  it("flags quantity below 1", () => {
    render(<Harness initial={[slot()]} />);
    fireEvent.change(screen.getByLabelText("Slot 1 quantity needed"), {
      target: { value: "0" },
    });
    expect(screen.getByLabelText("Slot 1 quantity needed")).toBeInvalid();
  });

  it("removes a slot", () => {
    render(<Harness initial={[slot(), slot({ id: "s2", title: "Soda" })]} />);
    fireEvent.click(screen.getByRole("button", { name: "Remove slot 1" }));
    expect(out()).toHaveLength(1);
    expect(out()[0].id).toBe("s2");
  });
});

describe("EventCreateModal contribution slots", () => {
  const base = {
    id: "e1",
    title: "Party",
    description: null,
    location: null,
    latitude: null,
    longitude: null,
    starts_at: "2026-05-01T10:00:00Z",
    ends_at: "2026-05-01T12:00:00Z",
    is_all_day: false,
    visibility: "community",
    subgroup_id: null,
    color: null,
    contribution_slots: [slot()],
  } as unknown as EventItem;

  it("pre-fills slots in edit mode and submits them", async () => {
    render(<EventCreateModal open onClose={() => {}} event={base} />);
    expect(screen.getByLabelText("Slot 1 title")).toHaveValue("Cake");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(updateMutate).toHaveBeenCalled());
    expect(updateMutate.mock.calls[0][0].contribution_slots).toEqual([slot()]);
  });

  it("submits new slots on create", async () => {
    render(<EventCreateModal open onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "X" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add slot" }));
    fireEvent.change(screen.getByLabelText("Slot 1 title"), {
      target: { value: "Chips" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(createMutate).toHaveBeenCalled());
    expect(createMutate.mock.calls[0][0].contribution_slots).toEqual([
      {
        id: null,
        title: "Chips",
        quantity_needed: 1,
        quantity_claimed: 0,
        claimed_by: [],
      },
    ]);
  });
});
