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
    // ThemeProvider injects a <script>; assert no media markup instead.
    expect(container.querySelector("div, img, video")).toBeNull();
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

  it("shows a Report button per tile only when canReport", () => {
    const { rerender, queryAllByRole } = renderWithProviders(
      <PostMedia media={[mk("a"), mk("b")]} />,
    );
    expect(queryAllByRole("button", { name: /report/i })).toHaveLength(0);
    rerender(<PostMedia media={[mk("a"), mk("b")]} canReport />);
    expect(queryAllByRole("button", { name: /report/i })).toHaveLength(2);
  });

  it("Report click does not trigger the tile onClick", () => {
    const onClick = vi.fn();
    const { getByRole } = renderWithProviders(
      <PostMedia media={[mk("a")]} canReport onClick={onClick} />,
    );
    fireEvent.click(getByRole("button", { name: /report/i }));
    expect(onClick).not.toHaveBeenCalled();
  });
});
