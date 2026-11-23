/**
 * @file tests/unit/audio/Recorder.test.tsx
 * @brief Recorder with MediaRecorder/getUserMedia mocked: mime pick, timer,
 *        15-minute auto-stop, permission denied, retake and upload.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const singleUpload = vi.hoisted(() => vi.fn());
const waitUntilReady = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/media", () => ({ singleUpload, waitUntilReady }));

import { Recorder } from "@/components/audio/Recorder";
import { pickMime, fmtTime, MAX_SECS } from "@/components/audio/useRecorder";

let supported: string[] = [];
let last: FakeRecorder;

class FakeRecorder {
  state = "inactive";
  mimeType: string;
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  static isTypeSupported = (t: string) => supported.includes(t);
  constructor(_s: unknown, o: { mimeType: string }) {
    this.mimeType = o.mimeType;
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    last = this;
  }
  start() {
    this.state = "recording";
  }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["abc"]) });
    this.onstop?.();
  }
}

const stream = { getTracks: () => [{ stop: vi.fn() }] };

beforeEach(() => {
  supported = [];
  vi.stubGlobal("MediaRecorder", FakeRecorder);
  URL.createObjectURL = vi.fn(() => "blob:x");
  URL.revokeObjectURL = vi.fn();
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
  });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("Recorder", () => {
  it("prefers audio/mp4 and falls back to audio/webm", () => {
    expect(pickMime()).toBe("audio/webm");
    supported = ["audio/mp4"];
    expect(pickMime()).toBe("audio/mp4");
    expect(fmtTime(75)).toBe("1:15");
  });

  it("records, reviews, retakes, then uploads and reports ready media", async () => {
    supported = ["audio/mp4"];
    singleUpload.mockResolvedValue({ id: "m1" });
    waitUntilReady.mockResolvedValue({ id: "m1", status: "ready" });
    const onReady = vi.fn();
    render(<Recorder onReady={onReady} />);
    await userEvent.click(screen.getByRole("button", { name: /record/i }));
    expect(last.mimeType).toBe("audio/mp4");
    expect(screen.getByRole("timer")).toHaveTextContent("0:00 / 15:00");
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    expect(screen.getByLabelText("Preview recording")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /retake/i }));
    expect(screen.getByRole("button", { name: /record/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /record/i }));
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    await userEvent.click(
      screen.getByRole("button", { name: /use recording/i }),
    );
    const file = singleUpload.mock.calls[0][0] as File;
    expect(file.name).toBe("voice-note.m4a");
    expect(file.type).toBe("audio/mp4");
    expect(onReady).toHaveBeenCalledWith({ id: "m1", status: "ready" });
  });

  it("shows a clear message when the microphone is blocked", async () => {
    (
      navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>
    ).mockRejectedValue(new DOMException("no", "NotAllowedError"));
    render(<Recorder onReady={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /record/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /microphone access is blocked.*allow the microphone/i,
    );
  });

  it("auto-stops at 15 minutes", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<Recorder onReady={vi.fn()} />);
    await act(async () => {
      screen.getByRole("button", { name: /record/i }).click();
    });
    await act(async () => {
      vi.advanceTimersByTime((MAX_SECS + 1) * 1000);
    });
    expect(last.state).toBe("inactive");
    expect(screen.getByLabelText("Preview recording")).toBeInTheDocument();
  });
});
