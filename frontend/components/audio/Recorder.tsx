"use client";
/**
 * @file components/audio/Recorder.tsx
 * @brief Voice recorder: record with a timer (auto-stops at 15 min), review,
 *        retake, then upload and wait for the m4a transcode.
 */
import * as React from "react";
import { Mic, RotateCcw, Square } from "lucide-react";
import { Button } from "@/components/ui";
import { fmtTime, MAX_SECS, useRecorder } from "@/components/audio/useRecorder";
import { singleUpload, waitUntilReady, type MediaItem } from "@/lib/api/media";

/**
 * @brief Inline recorder.
 * @param onReady called with the processed (ready) audio media
 * @param onCancel optional close handler
 * @return recorder element
 */
export function Recorder({
  onReady,
  onCancel,
}: {
  onReady: (media: MediaItem) => void;
  onCancel?: () => void;
}) {
  const r = useRecorder();
  const [busy, setBusy] = React.useState(false);

  const use = async () => {
    if (!r.blob) return;
    setBusy(true);
    r.setError(null);
    try {
      const ext = r.blob.type === "audio/mp4" ? "m4a" : "webm";
      const file = new File([r.blob], `voice-note.${ext}`, {
        type: r.blob.type,
      });
      const m = await singleUpload(file);
      onReady(await waitUntilReady(m.id));
      r.retake();
    } catch {
      r.setError("Couldn't save your recording. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      role="group"
      aria-label="Voice recorder"
      className="mt-2 flex flex-col gap-2 rounded-2xl bg-bg p-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        {r.state === "idle" && (
          <Button size="sm" className="min-h-11" onClick={r.start}>
            <Mic className="size-4" aria-hidden /> Record
          </Button>
        )}
        {r.state === "recording" && (
          <Button
            size="sm"
            variant="destructive"
            className="min-h-11"
            onClick={r.stop}
          >
            <Square className="size-4" aria-hidden /> Stop
          </Button>
        )}
        {r.state !== "review" && (
          <span
            role="timer"
            aria-label="Recording time"
            className="font-mono text-sm tabular-nums text-ink"
          >
            {fmtTime(r.secs)} / {fmtTime(MAX_SECS)}
          </span>
        )}
        {r.state === "review" && r.url && (
          <>
            <audio
              src={r.url}
              controls
              aria-label="Preview recording"
              className="h-11 min-w-0 flex-1"
            />
            <Button
              size="sm"
              variant="ghost"
              className="min-h-11"
              onClick={r.retake}
              disabled={busy}
            >
              <RotateCcw className="size-4" aria-hidden /> Retake
            </Button>
            <Button size="sm" className="min-h-11" onClick={use} loading={busy}>
              Use recording
            </Button>
          </>
        )}
        {onCancel && r.state !== "recording" && (
          <Button
            size="sm"
            variant="ghost"
            className="min-h-11"
            onClick={onCancel}
            disabled={busy}
          >
            Cancel
          </Button>
        )}
      </div>
      <p className="sr-only" role="status" aria-live="polite">
        {r.state === "recording" ? "Recording" : ""}
      </p>
      {r.error && (
        <p role="alert" className="text-sm text-danger">
          {r.error}
        </p>
      )}
    </div>
  );
}

export default Recorder;
