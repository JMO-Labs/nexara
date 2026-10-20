/**
 * @file tests/unit/components/layout/ModalRoot.test.tsx
 * @brief Smoke tests asserting QuickActions modal keys open the correct modals.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
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

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("ModalRoot modal key wiring", () => {
  beforeEach(() => {
    useModals.getState().close();
  });

  it("create-post key mounts PostComposer inside a Modal", () => {
    wrap(<ModalRoot />);
    useModals.getState().show("create-post");
    // Re-render by re-wrapping (store is reactive)
    wrap(<ModalRoot />);
    expect(screen.getAllByTestId("post-composer").length).toBeGreaterThan(0);
  });

  it("create-event key mounts EventCreateModal", () => {
    useModals.getState().show("create-event");
    wrap(<ModalRoot />);
    expect(screen.getByTestId("event-create-modal")).toBeInTheDocument();
  });

  it("create-gallery key mounts GalleryCreateModal", () => {
    useModals.getState().show("create-gallery");
    wrap(<ModalRoot />);
    expect(screen.getByTestId("gallery-create-modal")).toBeInTheDocument();
  });

  it("no key → no modal content rendered", () => {
    wrap(<ModalRoot />);
    expect(screen.queryByTestId("event-create-modal")).toBeNull();
    expect(screen.queryByTestId("gallery-create-modal")).toBeNull();
  });
});
