/**
 * @file tests/unit/galleries/brand-upload.test.tsx
 * @brief Brand rules for the gallery uploader: glass drop zone, ink
 *        "Choose files" pill.
 */
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { GalleryUpload } from "@/components/galleries/GalleryUpload";

vi.mock("@/lib/api/galleries");
vi.mock("@/lib/api/media");

function renderUpload() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <GalleryUpload galleryId="g1" />
    </QueryClientProvider>,
  );
}

describe("GalleryUpload brand", () => {
  it("drop zone is a glass item, not a dashed hard box", () => {
    renderUpload();
    const zone = screen.getByTestId("upload-dropzone");
    expect(zone.className).toContain("glass-item");
    expect(zone.className).not.toContain("border-dashed");
    expect(zone.className).toContain("rounded-[28px]");
  });

  it("Choose files is the ink primary pill", () => {
    renderUpload();
    const btn = screen.getByRole("button", { name: "Choose files" });
    expect(btn.className).toContain("bg-surface-strong");
  });
});
