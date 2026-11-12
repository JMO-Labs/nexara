/**
 * @file tests/unit/content/VideoEmbed.test.tsx
 * @brief VideoEmbed click-to-play, provider URLs, sandbox and a11y.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VideoEmbed, embedUrl } from "@/components/content/VideoEmbed";
import type { LinkPreview } from "@/lib/api/posts";

const mk = (provider_type: string, provider_id = "abc123"): LinkPreview => ({
  id: "lp1",
  url: "https://example.com/v",
  og_title: "Clip",
  og_description: null,
  og_image: "https://peer.example.org/lazy-static/previews/x.jpg",
  og_site_name: null,
  provider_type,
  provider_id,
});

describe("VideoEmbed", () => {
  it("renders thumbnail and play button, no iframe", () => {
    const { container } = render(<VideoEmbed preview={mk("youtube")} />);
    expect(screen.getByRole("img", { name: "Clip" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Video: youtube, click to play" }),
    ).toBeInTheDocument();
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("uses thumbnail prop when no og_image", () => {
    const p = { ...mk("vimeo"), og_image: null };
    render(<VideoEmbed preview={p} thumbnail="https://t.example/t.png" />);
    expect(screen.getByRole("img").getAttribute("src")).toBe(
      "https://t.example/t.png",
    );
  });

  it("loads sandboxed iframe on click", () => {
    const { container } = render(<VideoEmbed preview={mk("youtube")} />);
    fireEvent.click(screen.getByRole("button"));
    const f = container.querySelector("iframe")!;
    expect(f.getAttribute("src")).toBe(
      "https://www.youtube.com/embed/abc123?rel=0",
    );
    expect(f.getAttribute("sandbox")).toBe(
      "allow-scripts allow-same-origin allow-presentation",
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it.each([
    ["youtube", "https://www.youtube.com/embed/abc123?rel=0"],
    ["vimeo", "https://player.vimeo.com/video/abc123"],
    ["twitch", "https://player.twitch.tv/?channel=abc123"],
    ["dailymotion", "https://www.dailymotion.com/embed/video/abc123"],
    ["peertube", "https://peer.example.org/videos/embed/abc123"],
  ])("embed url for %s", (type, url) => {
    expect(embedUrl(mk(type))).toBe(url);
  });

  it("twitch numeric id is a video", () => {
    expect(embedUrl(mk("twitch", "12345"))).toBe(
      "https://player.twitch.tv/?video=12345",
    );
  });

  it("returns null for unknown provider or unsafe id", () => {
    expect(embedUrl(mk("other"))).toBeNull();
    expect(embedUrl(mk("youtube", "a/../b"))).toBeNull();
  });
});
