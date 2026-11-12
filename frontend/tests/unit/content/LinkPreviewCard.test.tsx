/**
 * @file tests/unit/content/LinkPreviewCard.test.tsx
 * @brief LinkPreviewCard renders OG metadata, fallback, click and a11y.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LinkPreviewCard } from "@/components/content/LinkPreviewCard";
import type { LinkPreview } from "@/lib/api/posts";

const base: LinkPreview = {
  id: "lp1",
  url: "https://example.com/a",
  og_title: "Example title",
  og_description: "Example description",
  og_image: "https://example.com/i.png",
  og_site_name: "Example",
  provider_type: null,
  provider_id: null,
};

describe("LinkPreviewCard", () => {
  it("renders metadata and proxy image", () => {
    render(<LinkPreviewCard preview={base} />);
    expect(screen.getByText("Example title")).toBeInTheDocument();
    expect(screen.getByText("Example description")).toBeInTheDocument();
    expect(screen.getByText("Example")).toBeInTheDocument();
    const img = screen.getByRole("img", { name: "Example title" });
    expect(img.getAttribute("src")).toContain(
      "/api/v1/link-previews/lp1/image",
    );
  });

  it("shows fallback icon without image", () => {
    render(<LinkPreviewCard preview={{ ...base, og_image: null }} />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByTestId("link-preview-fallback")).toBeInTheDocument();
  });

  it("falls back when image fails to load", () => {
    render(<LinkPreviewCard preview={base} />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByTestId("link-preview-fallback")).toBeInTheDocument();
  });

  it("skips site name when absent", () => {
    render(<LinkPreviewCard preview={{ ...base, og_site_name: null }} />);
    expect(screen.queryByTestId("link-preview-site")).toBeNull();
  });

  it("opens in new tab and fires onClick", () => {
    const onClick = vi.fn();
    render(<LinkPreviewCard preview={base} onClick={onClick} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", base.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    fireEvent.click(link);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("truncates with line clamps and char limits", () => {
    render(
      <LinkPreviewCard
        preview={{
          ...base,
          og_title: "t".repeat(150),
          og_description: "d".repeat(300),
        }}
      />,
    );
    const title = screen.getByTestId("link-preview-title");
    const desc = screen.getByTestId("link-preview-description");
    expect(title.className).toContain("line-clamp-2");
    expect(desc.className).toContain("line-clamp-3");
    expect(title.textContent!.length).toBeLessThanOrEqual(100);
    expect(desc.textContent!.length).toBeLessThanOrEqual(200);
  });

  it("has screen reader text and focus ring", () => {
    render(<LinkPreviewCard preview={base} />);
    expect(
      screen.getByText("External link: Example title"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link").className).toContain("focus-visible:");
  });

  it("uses generic alt when no title", () => {
    render(<LinkPreviewCard preview={{ ...base, og_title: null }} />);
    expect(
      screen.getByRole("img", { name: "Link preview" }),
    ).toBeInTheDocument();
  });
  it("does not render a link for non-http(s) urls", () => {
    render(
      <LinkPreviewCard preview={{ ...base, url: "javascript:alert(1)" }} />,
    );
    expect(screen.queryByRole("link")).toBeNull();
  });
});
