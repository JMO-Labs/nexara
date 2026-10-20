/**
 * @file tests/unit/media/MediaCard.test.tsx
 * @brief Renders filename + formatted size; fires onSelect.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { MediaCard } from "@/components/media/MediaCard";
import type { MediaItem } from "@/lib/api/media";

const m: MediaItem = {
  id: "m1",
  filename: "photo.jpg",
  content_type: "image/jpeg",
  storage_key: "k",
  thumbnail_key: null,
  size_bytes: 2048,
  width: null,
  height: null,
  duration_secs: null,
  alt_text: null,
  status: "ready",
  created_at: "2026-04-25T00:00:00Z",
};

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("MediaCard", () => {
  it("renders filename + formatted size", () => {
    wrap(<MediaCard media={m} />);
    expect(screen.getByText("photo.jpg")).toBeInTheDocument();
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  });
  it("fires onSelect on click", () => {
    const fn = vi.fn();
    wrap(<MediaCard media={m} onSelect={fn} />);
    fireEvent.click(screen.getByRole("button"));
    expect(fn).toHaveBeenCalledWith(m);
  });
});
