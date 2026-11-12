/**
 * @file tests/unit/feed/PostMedia.test.tsx
 * @brief PostMedia: images, videos, overflow, empty, click.
 */
import { describe, it, expect, vi } from "vitest";
import { fireEvent } from "@testing-library/react";
import { PostMedia } from "@/components/feed/PostMedia";
import type { PostMedia as Media } from "@/lib/api/posts";
import { renderWithProviders } from "../../utils/renderWithProviders";

const mk = (id: string, mime = "image/png"): Media => ({
  id,
  url: `/m/${id}`,
  thumbnail_url: mime.startsWith("image/") ? `/t/${id}` : null,
  mime_type: mime,
  width: null,
  height: null,
});

describe("PostMedia", () => {
  it("renders nothing for empty media", () => {
    const { container } = renderWithProviders(<PostMedia media={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders image using thumbnail and video using url", () => {
    const { container } = renderWithProviders(
      <PostMedia media={[mk("a"), mk("b", "video/mp4")]} />,
    );
    expect(container.querySelector("img")).toHaveAttribute("src", "/t/a");
    expect(container.querySelector("video")).toHaveAttribute("src", "/m/b");
  });

  it("falls back to url when image has no thumbnail", () => {
    const m = { ...mk("a"), thumbnail_url: null };
    const { container } = renderWithProviders(<PostMedia media={[m]} />);
    expect(container.querySelector("img")).toHaveAttribute("src", "/m/a");
  });

  it("caps at four tiles with +N overflow", () => {
    const media = ["a", "b", "c", "d", "e", "f"].map((id) => mk(id));
    const { container, getByText } = renderWithProviders(
      <PostMedia media={media} />,
    );
    expect(container.querySelectorAll("img")).toHaveLength(4);
    expect(getByText("+2")).toBeInTheDocument();
  });

  it("calls onClick with tile index", () => {
    const onClick = vi.fn();
    const { container } = renderWithProviders(
      <PostMedia media={[mk("a"), mk("b")]} onClick={onClick} />,
    );
    fireEvent.click(container.querySelectorAll("img")[1]);
    expect(onClick).toHaveBeenCalledWith(1);
  });
});
