"use client";
/**
 * @file components/audio/useRecorder.ts
 * @brief MediaRecorder state machine: idle -> recording -> review, with a
 *        15-minute auto-stop and a clear message when the mic is blocked.
 */
import * as React from "react";

/** @brief Longest recording in seconds (server rejects anything longer). */
export const MAX_SECS = 900;

export const DENIED_MESSAGE =
  "Microphone access is blocked. Allow the microphone for this site in your browser's address bar or settings, then try again.";

/**
 * @brief Pick the best supported container (m4a on Safari, webm elsewhere).
 * @return "audio/mp4" when supported, else "audio/webm"
 */
export function pickMime(): string {
  const ok =
    typeof MediaRecorder !== "undefined" &&
    typeof MediaRecorder.isTypeSupported === "function" &&
    MediaRecorder.isTypeSupported("audio/mp4");
  return ok ? "audio/mp4" : "audio/webm";
}

/**
 * @brief Recorder controller.
 * @return state, elapsed seconds, blob, preview url, error and actions
 */
export function useRecorder() {
  const [state, setState] = React.useState<"idle" | "recording" | "review">(
    "idle",
  );
  const [secs, setSecs] = React.useState(0);
  const [blob, setBlob] = React.useState<Blob | null>(null);
  const [url, setUrl] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const rec = React.useRef<MediaRecorder | null>(null);
  const timer = React.useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  };
  const stop = React.useCallback(() => {
    clearTimer();
    if (rec.current && rec.current.state !== "inactive") rec.current.stop();
  }, []);

  const start = React.useCallback(async () => {
    setError(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError(DENIED_MESSAGE);
      return;
    }
    const type = pickMime();
    const chunks: Blob[] = [];
    const r = new MediaRecorder(stream, { mimeType: type });
    r.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    r.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const b = new Blob(chunks, { type });
      setBlob(b);
      setUrl(URL.createObjectURL(b));
      setState("review");
    };
    rec.current = r;
    r.start();
    const t0 = Date.now();
    setSecs(0);
    setState("recording");
    timer.current = setInterval(() => {
      const s = Math.floor((Date.now() - t0) / 1000);
      setSecs(Math.min(s, MAX_SECS));
      if (s >= MAX_SECS) stop();
    }, 250);
  }, [stop]);

  const retake = React.useCallback(() => {
    if (url) URL.revokeObjectURL(url);
    setBlob(null);
    setUrl(null);
    setSecs(0);
    setState("idle");
  }, [url]);

  React.useEffect(
    () => () => {
      clearTimer();
      if (rec.current && rec.current.state !== "inactive") rec.current.stop();
    },
    [],
  );

  return { state, secs, blob, url, error, start, stop, retake, setError };
}

/**
 * @param secs elapsed seconds
 * @return "m:ss"
 */
export const fmtTime = (secs: number) =>
  `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
