/**
 * @file tests/unit/audio/PostMediaAudio.test.tsx
 * @brief Audio attachments render a player; images keep the grid.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PostMedia } from "@/components/feed/PostMedia";

const base = { thumbnail_url: null, width: null, height: null };

describe("PostMedia audio", () => {
  it("renders an audio player, no video tag, for audio media", () => {
    const { container } = render(
      <PostMedia
        media={[
          {
            ...base,
            id: "a1",
            url: "/api/v1/media/a1/file",
            mime_type: "audio/mp4",
          },
        ]}
      />,
    );
    expect(screen.getByLabelText("Voice note").tagName).toBe("AUDIO");
    expect(container.querySelector("video")).toBeNull();
  });
});
