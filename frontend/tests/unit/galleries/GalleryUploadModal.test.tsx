/**
 * @file tests/unit/galleries/GalleryUploadModal.test.tsx
 * @brief GalleryUploadModal: pick gallery, choose files -> upload API; cancel.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { GalleryUploadModal } from "@/components/galleries/GalleryUploadModal";
import * as galleryApi from "@/lib/api/galleries";
import * as mediaApi from "@/lib/api/media";

vi.mock("@/lib/api/galleries");
vi.mock("@/lib/api/media");
// Radix Select is unreliable in jsdom: swap for a native <select>.
vi.mock("@/components/ui", async (orig) => {
  const actual = await orig<typeof import("@/components/ui")>();
  return {
    ...actual,
    Select: ({
      label,
      onValueChange,
      children,
    }: {
      label: string;
      onValueChange: (v: string) => void;
      children: React.ReactNode;
    }) => (
      <select
        aria-label={label}
        defaultValue=""
        onChange={(e) => onValueChange(e.target.value)}
      >
        <option value="" />
        {children}
      </select>
    ),
    Option: ({
      value,
      children,
    }: {
      value: string;
      children: React.ReactNode;
    }) => <option value={value}>{children}</option>,
  };
});

describe("GalleryUploadModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(galleryApi.listGalleries).mockResolvedValue({
      items: [{ id: "g1", title: "Trip" }],
    } as unknown as Awaited<ReturnType<typeof galleryApi.listGalleries>>);
  });

  it("uploads selected files into the chosen gallery", async () => {
    vi.mocked(mediaApi.uploadFile).mockResolvedValue({
      id: "media-1",
    } as Awaited<ReturnType<typeof mediaApi.uploadFile>>);
    vi.mocked(galleryApi.addItem).mockResolvedValue(
      {} as Awaited<ReturnType<typeof galleryApi.addItem>>,
    );
    const { baseElement } = renderWithProviders(
      <GalleryUploadModal open onClose={() => {}} subgroupId="s1" />,
    );
    await screen.findByRole("option", { name: "Trip" });
    fireEvent.change(screen.getByLabelText("Select a gallery"), {
      target: { value: "g1" },
    });
    const input = await waitFor(() => {
      const el = baseElement.querySelector('input[type="file"]');
      expect(el).not.toBeNull();
      return el as HTMLInputElement;
    });
    const file = new File(["a"], "a.jpg", { type: "image/jpeg" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(mediaApi.uploadFile).toHaveBeenCalled());
    expect(vi.mocked(mediaApi.uploadFile).mock.calls[0][0]).toBe(file);
    await waitFor(() =>
      expect(galleryApi.addItem).toHaveBeenCalledWith("g1", "media-1"),
    );
  });

  it("cancel closes the modal", async () => {
    const onClose = vi.fn();
    renderWithProviders(
      <GalleryUploadModal open onClose={onClose} subgroupId="s1" />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
