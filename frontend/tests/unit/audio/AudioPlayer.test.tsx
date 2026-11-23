/**
 * @file tests/unit/audio/AudioPlayer.test.tsx
 * @brief Native audio controls and the 1x / 1.5x speed toggle.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AudioPlayer } from "@/components/audio/AudioPlayer";

describe("AudioPlayer", () => {
  it("renders a native audio element with controls", () => {
    render(<AudioPlayer src="/api/v1/media/m1/file" label="Story" />);
    const audio = screen.getByLabelText("Story") as HTMLAudioElement;
    expect(audio.tagName).toBe("AUDIO");
    expect(audio.controls).toBe(true);
    expect(audio.getAttribute("src")).toBe("/api/v1/media/m1/file");
  });

  it("toggles playback rate between 1x and 1.5x", async () => {
    render(<AudioPlayer src="/x" />);
    const audio = screen.getByLabelText("Voice note") as HTMLAudioElement;
    const btn = screen.getByRole("button", { name: /1.5 times speed/i });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(btn);
    expect(btn).toHaveAttribute("aria-pressed", "true");
    expect(audio.playbackRate).toBe(1.5);
    await userEvent.click(btn);
    expect(audio.playbackRate).toBe(1);
  });
});
