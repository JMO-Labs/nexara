/**
 * @file tests/unit/media/CoverPicker.test.tsx
 * @brief CoverPicker: link import, validation, remove.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const importMediaUrl = vi.fn();
vi.mock("@/lib/api/media", () => ({
  importMediaUrl: (u: string) => importMediaUrl(u),
}));
vi.mock("@/hooks/useMediaUpload", () => ({
  useMediaUpload: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: ({ mediaId }: { mediaId: string }) => <img alt={mediaId} />,
}));

import { CoverPicker } from "@/components/media/CoverPicker";

describe("CoverPicker", () => {
  beforeEach(() => {
    importMediaUrl.mockReset();
  });

  it("imports a pasted link and emits the media id", async () => {
    importMediaUrl.mockResolvedValue({ id: "m9" });
    const onChange = vi.fn();
    renderWithProviders(<CoverPicker mediaId={null} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: /Use a link/ }));
    fireEvent.change(screen.getByLabelText("Image link"), {
      target: { value: " https://x.test/a.jpg " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("m9"));
    expect(importMediaUrl).toHaveBeenCalledWith("https://x.test/a.jpg");
  });

  it("rejects non-http links and shows server errors", async () => {
    renderWithProviders(<CoverPicker mediaId={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Use a link/ }));
    const input = screen.getByLabelText("Image link");
    fireEvent.change(input, { target: { value: "ftp://nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/http/);
    expect(importMediaUrl).not.toHaveBeenCalled();
    importMediaUrl.mockRejectedValue(new Error("That link can't be used"));
    fireEvent.change(input, { target: { value: "https://10.0.0.1/a.png" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(
      await screen.findByText("That link can't be used"),
    ).toBeInTheDocument();
  });

  it("Remove clears the cover", () => {
    const onChange = vi.fn();
    renderWithProviders(<CoverPicker mediaId="m1" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
