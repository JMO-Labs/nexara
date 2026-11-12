/**
 * @file tests/unit/media/MediaSelector.test.tsx
 * @brief MediaSelector: tabs, upload select, gallery select, URL validation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const listMedia = vi.fn();
let onComplete: ((m: unknown) => void) | undefined;
vi.mock("@/lib/api/media", () => ({
  listMedia: (...a: unknown[]) => listMedia(...a),
  mediaFileUrl: (id: string) => `/f/${id}`,
  mediaThumbUrl: (id: string) => `/t/${id}`,
}));
vi.mock("@/components/media/UploadZone", () => ({
  UploadZone: (p: { onComplete: (m: unknown) => void }) => {
    onComplete = p.onComplete;
    return <div>zone</div>;
  },
}));
import { MediaSelector } from "@/components/media/MediaSelector";

const item = { id: "m1", filename: "cat.png", thumbnail_key: null };

function setup() {
  const onSelect = vi.fn();
  const onClose = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MediaSelector open onClose={onClose} onSelect={onSelect} />
    </QueryClientProvider>,
  );
  return { onSelect, onClose };
}

describe("MediaSelector", () => {
  beforeEach(() => {
    listMedia.mockReset();
    listMedia.mockResolvedValue({ items: [item], next_cursor: null });
  });

  it("renders three tabs", () => {
    setup();
    for (const n of ["Upload", "Gallery", "URL"])
      expect(screen.getByRole("tab", { name: n })).toBeTruthy();
  });

  it("upload completion selects media", async () => {
    const { onSelect, onClose } = setup();
    onComplete?.(item);
    await waitFor(() =>
      expect(onSelect).toHaveBeenCalledWith({
        mediaId: "m1",
        url: "/f/m1",
        alt: "cat.png",
      }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("gallery click selects", async () => {
    const { onSelect } = setup();
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Gallery" }));
    fireEvent.click(await screen.findByRole("button", { name: "cat.png" }));
    expect(onSelect).toHaveBeenCalledWith({
      mediaId: "m1",
      url: "/f/m1",
      alt: "cat.png",
    });
  });

  it("URL tab validates, previews, and submits", () => {
    const { onSelect } = setup();
    fireEvent.mouseDown(screen.getByRole("tab", { name: "URL" }));
    const input = screen.getByLabelText("Image URL");
    fireEvent.change(input, { target: { value: "ftp://x" } });
    fireEvent.blur(input);
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "Use URL" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    fireEvent.change(input, { target: { value: "https://a.b/c.png" } });
    fireEvent.blur(input);
    expect(screen.getByAltText("Preview").getAttribute("src")).toBe(
      "https://a.b/c.png",
    );
    fireEvent.click(screen.getByRole("button", { name: "Use URL" }));
    expect(onSelect).toHaveBeenCalledWith({
      mediaId: null,
      url: "https://a.b/c.png",
      alt: "https://a.b/c.png",
    });
  });
});
