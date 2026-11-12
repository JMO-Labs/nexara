/**
 * @file tests/unit/components/layout/ModalRoot.test.tsx
 * @brief Smoke tests asserting QuickActions modal keys open the correct modals.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { useModals } from "@/stores/modals";

// Mock heavy sub-components to keep the test fast.
vi.mock("@/components/search/GlobalCommandPalette", () => ({
  GlobalCommandPalette: () => null,
}));
vi.mock("@/components/ui/Toast", () => ({ ToastRoot: () => null }));
vi.mock("@/components/feed/PostComposer", () => ({
  PostComposer: () => <div data-testid="post-composer" />,
}));
vi.mock("@/components/events/EventCreateModal", () => ({
  EventCreateModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="event-create-modal" /> : null,
}));
vi.mock("@/components/galleries/GalleryCreateModal", () => ({
  GalleryCreateModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="gallery-create-modal" /> : null,
}));

import { ModalRoot } from "@/components/layout/ModalRoot";

describe("ModalRoot modal key wiring", () => {
  beforeEach(() => {
    useModals.getState().close();
  });

  it("create-post key mounts PostComposer inside a Modal", async () => {
    render(<ModalRoot />);
    act(() => useModals.getState().show("create-post"));
    expect(await screen.findByTestId("post-composer")).toBeInTheDocument();
  });

  it("create-event key mounts EventCreateModal", async () => {
    useModals.getState().show("create-event");
    render(<ModalRoot />);
    expect(await screen.findByTestId("event-create-modal")).toBeInTheDocument();
  });

  it("create-gallery key mounts GalleryCreateModal", async () => {
    useModals.getState().show("create-gallery");
    render(<ModalRoot />);
    expect(
      await screen.findByTestId("gallery-create-modal"),
    ).toBeInTheDocument();
  });

  it("no key → no modal content rendered", () => {
    render(<ModalRoot />);
    expect(screen.queryByTestId("event-create-modal")).toBeNull();
    expect(screen.queryByTestId("gallery-create-modal")).toBeNull();
  });
});
