"use client";
/**
 * @file components/media/UploadZone.tsx
 * @brief Drag-and-drop + click-to-pick upload zone. Sequential uploads with
 *        per-file progress.
 */
import * as React from "react";
import { Button } from "@/components/ui";
import { uploadFile, type MediaItem } from "@/lib/api/media";

export interface UploadZoneProps {
  onComplete?: (media: MediaItem) => void;
}

interface Job {
  file: File;
  progress: number;
  done: boolean;
  error: string | null;
}

export function UploadZone({ onComplete }: UploadZoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [dragOver, setDragOver] = React.useState(false);

  const start = React.useCallback(
    async (files: File[]) => {
      const initial: Job[] = files.map((f) => ({
        file: f,
        progress: 0,
        done: false,
        error: null,
      }));
      setJobs((j) => [...j, ...initial]);
      const offset = jobs.length;
      for (let i = 0; i < files.length; i++) {
        const idx = offset + i;
        try {
          const m = await uploadFile(files[i], (pct) =>
            setJobs((js) =>
              js.map((j, ji) => (ji === idx ? { ...j, progress: pct } : j)),
            ),
          );
          setJobs((js) =>
            js.map((j, ji) =>
              ji === idx ? { ...j, done: true, progress: 100 } : j,
            ),
          );
          onComplete?.(m);
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          setJobs((js) =>
            js.map((j, ji) => (ji === idx ? { ...j, error: msg } : j)),
          );
        }
      }
    },
    [jobs.length, onComplete],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    void start(Array.from(e.dataTransfer.files));
  };

  return (
    <div className="flex flex-col gap-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`rounded-2xl border-2 border-dashed p-8 text-center motion-safe:transition-colors ${dragOver ? "border-accent bg-surface-strong/10" : "border-current/30 bg-surface"}`}
      >
        <p className="text-lg font-semibold">Drop files here</p>
        <p className="text-sm text-muted">or choose them from your device</p>
        <Button
          className="mt-4 min-h-11"
          size="sm"
          variant="outline"
          type="button"
          onClick={() => inputRef.current?.click()}
        >
          Choose files
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          aria-label="Upload media files"
          onChange={(e) => {
            if (e.target.files) void start(Array.from(e.target.files));
            e.target.value = "";
          }}
        />
      </div>
      {jobs.length > 0 && (
        <ul className="flex flex-col gap-2">
          {jobs.map((j, i) => (
            <li key={i} className="flex flex-col gap-1">
              <div className="flex justify-between gap-2 text-sm">
                <span className="flex-1 truncate">{j.file.name}</span>
                <span
                  className={j.error ? "text-destructive" : "text-muted"}
                  role={j.error ? "alert" : undefined}
                >
                  {j.error
                    ? j.error
                    : j.done
                      ? "Done"
                      : `${Math.round(j.progress)}%`}
                </span>
              </div>
              <div
                role="progressbar"
                aria-label={`Upload progress for ${j.file.name}`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(j.progress)}
                className="h-1.5 overflow-hidden rounded-full bg-surface"
              >
                <div
                  className={`h-full ${j.error ? "bg-destructive" : "bg-accent"}`}
                  style={{ width: `${j.progress}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default UploadZone;
