/**
 * @file tests/unit/galleries/GalleryUpload.test.tsx
 * @brief Drag-drop bulk uploader — 3 files create 3 rows, error shows retry.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GalleryUpload } from "@/components/galleries/GalleryUpload";
import * as galleryApi from "@/lib/api/galleries";
import * as mediaApi from "@/lib/api/media";

vi.mock("@/lib/api/galleries");
vi.mock("@/lib/api/media");

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("GalleryUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("drop 3 files renders 3 rows with progress", async () => {
    const files = [
      new File(["a"], "a.jpg", { type: "image/jpeg" }),
      new File(["b"], "b.jpg", { type: "image/jpeg" }),
      new File(["c"], "c.jpg", { type: "image/jpeg" }),
    ];

    vi.mocked(mediaApi.uploadFile).mockResolvedValue({
      id: "media-1",
      filename: "a.jpg",
      content_type: "image/jpeg",
      storage_key: "key",
      thumbnail_key: null,
      size_bytes: 100,
      width: 800,
      height: 600,
      duration_secs: null,
      alt_text: null,
      status: "ready",
      created_at: "2026-04-27T00:00:00Z",
    });

    vi.mocked(galleryApi.bulkAddItems).mockResolvedValue([]);

    wrap(<GalleryUpload galleryId="g1" />);
    const dropzone = screen.getByTestId("upload-dropzone");

    fireEvent.drop(dropzone, { dataTransfer: { files } });

    await waitFor(() => {
      const rows = screen.getAllByTestId("upload-row");
      expect(rows).toHaveLength(3);
    });

    const filenames = screen.getAllByTestId("upload-filename");
    expect(filenames[0]).toHaveTextContent("a.jpg");
    expect(filenames[1]).toHaveTextContent("b.jpg");
    expect(filenames[2]).toHaveTextContent("c.jpg");
  });

  it("error preserves row with retry button", async () => {
    const file = new File(["test"], "error.jpg", { type: "image/jpeg" });
    let attempt = 0;

    vi.mocked(mediaApi.uploadFile).mockImplementation(async () => {
      attempt++;
      if (attempt === 1) throw new Error("Upload failed");
      return {
        id: "media-ok",
        filename: "error.jpg",
        content_type: "image/jpeg",
        storage_key: "key",
        thumbnail_key: null,
        size_bytes: 100,
        width: 800,
        height: 600,
        duration_secs: null,
        alt_text: null,
        status: "ready",
        created_at: "2026-04-27T00:00:00Z",
      };
    });

    vi.mocked(galleryApi.bulkAddItems).mockResolvedValue([]);

    wrap(<GalleryUpload galleryId="g1" />);
    const dropzone = screen.getByTestId("upload-dropzone");

    fireEvent.drop(dropzone, { dataTransfer: { files: [file] } });

    // error row appears with retry button
    await waitFor(() => {
      expect(screen.getByText("Upload failed")).toBeInTheDocument();
    });

    expect(screen.getByTestId("upload-row")).toBeInTheDocument();
    expect(screen.getByTestId("retry-button")).toBeInTheDocument();

    // click retry
    fireEvent.click(screen.getByTestId("retry-button"));

    // succeeds on retry
    await waitFor(() => {
      expect(screen.getByText("Done")).toBeInTheDocument();
    });
  });

  it("has a visible Choose files button as keyboard path", () => {
    wrap(<GalleryUpload galleryId="g1" />);
    expect(
      screen.getByRole("button", { name: "Choose files" }),
    ).toBeInTheDocument();
  });
});
