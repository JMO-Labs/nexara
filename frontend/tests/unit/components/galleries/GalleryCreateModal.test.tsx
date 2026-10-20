/**
 * @file tests/unit/components/galleries/GalleryCreateModal.test.tsx
 * @brief GalleryCreateModal: submit payload and validation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GalleryCreateModal } from "@/components/galleries/GalleryCreateModal";

const mutateAsync = vi.fn().mockResolvedValue({});
vi.mock("@/hooks/useGalleries", () => ({
  useCreateGallery: () => ({ mutateAsync, isPending: false }),
}));
vi.mock("@/hooks/useCalendars", () => ({
  useCalendars: () => ({
    data: [{ id: "c", kind: "subgroup", name: "G", subgroup_id: "sg-1" }],
  }),
}));

describe("GalleryCreateModal", () => {
  beforeEach(() => mutateAsync.mockClear());

  it("submits payload and closes", async () => {
    const onClose = vi.fn();
    render(<GalleryCreateModal open onClose={onClose} />);
    await userEvent.type(await screen.findByLabelText(/^title/i), "Trip");
    await userEvent.type(screen.getByLabelText(/description/i), "Fun");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(mutateAsync).toHaveBeenCalledWith({
      title: "Trip",
      description: "Fun",
      visibility: "community",
    });
  });

  it("uses defaultSubgroupId", async () => {
    render(
      <GalleryCreateModal open onClose={vi.fn()} defaultSubgroupId="sg-1" />,
    );
    await userEvent.type(await screen.findByLabelText(/^title/i), "Trip");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(mutateAsync.mock.calls[0][0]).toMatchObject({
      visibility: "subgroup",
      subgroup_id: "sg-1",
    });
  });

  it("shows validation message for subgroup without group", async () => {
    render(<GalleryCreateModal open onClose={vi.fn()} />);
    await userEvent.type(await screen.findByLabelText(/^title/i), "Trip");
    await userEvent.click(screen.getByLabelText("A specific group"));
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /choose a group/i,
    );
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});
