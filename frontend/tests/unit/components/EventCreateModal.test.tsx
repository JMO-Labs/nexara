/**
 * @file tests/unit/components/EventCreateModal.test.tsx
 * @brief EventCreateModal: prefill, submit payload, validation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { EventCreateModal } from "@/components/events/EventCreateModal";

const mockCalendars = [
  { id: "cal-1", kind: "subgroup", name: "My Group", subgroup_id: "sg-1" },
];
const mutateAsync = vi.fn().mockResolvedValue({});

function wrap(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

vi.mock("@/hooks/useEvents", () => ({
  useCreateEvent: () => ({ mutateAsync, isPending: false }),
  useUpdateEvent: () => ({ mutateAsync, isPending: false }),
}));
vi.mock("@/hooks/useCalendars", () => ({
  useCalendars: () => ({ data: mockCalendars }),
}));
vi.mock("@/hooks/useUserLocation", () => ({ useUserLocation: () => null }));

describe("EventCreateModal", () => {
  beforeEach(() => {
    mutateAsync.mockClear();
  });

  it("renders in create mode", async () => {
    wrap(<EventCreateModal open onClose={vi.fn()} />);
    expect(await screen.findByText(/new event/i)).toBeInTheDocument();
  });

  it("defaults to community scope", async () => {
    wrap(<EventCreateModal open onClose={vi.fn()} />);
    expect(await screen.findByLabelText("Community")).toBeChecked();
  });

  it("pre-fills subgroup scope and hides picker with defaultSubgroupId", async () => {
    wrap(<EventCreateModal open onClose={vi.fn()} defaultSubgroupId="sg-1" />);
    await screen.findByText(/new event/i);
    expect(screen.queryByLabelText("Community")).toBeNull();
    await userEvent.type(screen.getByLabelText(/^title/i), "Picnic");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(mutateAsync.mock.calls[0][0]).toMatchObject({
      visibility: "subgroup",
      subgroup_id: "sg-1",
    });
  });

  it("submits payload", async () => {
    const onClose = vi.fn();
    wrap(<EventCreateModal open onClose={onClose} />);
    await userEvent.type(await screen.findByLabelText(/^title/i), "Picnic");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(mutateAsync.mock.calls[0][0]).toMatchObject({
      title: "Picnic",
      visibility: "community",
      subgroup_id: null,
      is_all_day: false,
      location: null,
      color: null,
    });
  });

  it("sends auto_create_gallery when checkbox is checked", async () => {
    wrap(<EventCreateModal open onClose={vi.fn()} />);
    await userEvent.type(await screen.findByLabelText(/^title/i), "Picnic");
    await userEvent.click(screen.getByLabelText(/create gallery for photos/i));
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(mutateAsync.mock.calls[0][0]).toMatchObject({
      auto_create_gallery: true,
    });
  });

  it("defaults auto_create_gallery to false", async () => {
    wrap(<EventCreateModal open onClose={vi.fn()} />);
    await userEvent.type(await screen.findByLabelText(/^title/i), "Picnic");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(mutateAsync.mock.calls[0][0]).toMatchObject({
      auto_create_gallery: false,
    });
  });

  it("hides the gallery checkbox in edit mode", async () => {
    const event: any = {
      id: "evt-1",
      title: "Existing",
      starts_at: "2025-05-01T10:00:00Z",
      ends_at: "2025-05-01T11:00:00Z",
      is_all_day: false,
      visibility: "community",
    };
    wrap(<EventCreateModal open onClose={vi.fn()} event={event} />);
    await screen.findByText(/edit event/i);
    expect(screen.queryByLabelText(/create gallery for photos/i)).toBeNull();
  });

  it("shows validation message and does not submit for subgroup without group", async () => {
    wrap(<EventCreateModal open onClose={vi.fn()} />);
    await userEvent.type(await screen.findByLabelText(/^title/i), "Picnic");
    await userEvent.click(screen.getByLabelText("A specific group"));
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /choose a group/i,
    );
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("edit mode prefills and saves", async () => {
    const event: any = {
      id: "evt-1",
      title: "Existing",
      description: "",
      location: "",
      starts_at: "2025-05-01T10:00:00Z",
      ends_at: "2025-05-01T11:00:00Z",
      is_all_day: false,
      visibility: "community",
      subgroup_id: null,
      color: null,
      latitude: null,
      longitude: null,
    };
    wrap(
      <EventCreateModal
        open
        onClose={vi.fn()}
        event={event}
        defaultSubgroupId="sg-1"
      />,
    );
    expect(await screen.findByText(/edit event/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^title/i)).toHaveValue("Existing");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(mutateAsync.mock.calls[0][0]).toMatchObject({ title: "Existing" });
  });
});
