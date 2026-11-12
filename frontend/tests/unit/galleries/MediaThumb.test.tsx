/**
 * @file tests/unit/galleries/MediaThumb.test.tsx
 * @brief MediaThumb renders thumbnail with alt text and falls back to /file.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MediaThumb } from "@/components/galleries/MediaThumb";

describe("MediaThumb", () => {
  it("renders the thumbnail image with alt text", () => {
    render(<MediaThumb mediaId="m1" alt="Sunset" />);
    const img = screen.getByAltText("Sunset") as HTMLImageElement;
    expect(img.src).toContain("/api/v1/media/m1/thumbnail");
  });

  it("renders nothing without a media id", () => {
    const { container } = render(<MediaThumb mediaId={null} alt="x" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("falls back to /file once when the thumbnail fails (e.g. video)", () => {
    render(<MediaThumb mediaId="v1" alt="Clip" />);
    const img = screen.getByAltText("Clip") as HTMLImageElement;
    fireEvent.error(img);
    expect(img.src).toContain("/api/v1/media/v1/file");
    fireEvent.error(img);
    expect(img.src).toContain("/api/v1/media/v1/file");
  });

  it("applies the hover zoom class only when requested", () => {
    render(<MediaThumb mediaId="m1" alt="Z" zoomOnHover />);
    expect(screen.getByAltText("Z")).toHaveClass("nx-thumb");
  });
});
