"use client";
/**
 * @file components/galleries/GalleryUpload.tsx
 * @brief Drag-drop bulk uploader with a "Choose files" button and progress queue.
 */
import * as React from "react";
import { Image as ImageIcon, Check, X, RotateCw, Loader2 } from "lucide-react";
import { Button, IconButton } from "@/components/ui";
import { cn } from "@/lib/utils";
import { useGalleryUpload } from "@/hooks/useGalleryUpload";

export interface GalleryUploadProps {
  galleryId: string;
}

/**
 * @brief Bulk uploader for a gallery.
 * @param galleryId target gallery
 * @return dropzone + upload queue
 */
export function GalleryUpload({ galleryId }: GalleryUploadProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const { jobs, enqueue, retry } = useGalleryUpload(galleryId);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    void enqueue(Array.from(e.dataTransfer.files));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) void enqueue(Array.from(e.target.files));
    e.target.value = "";
  };

  return (
    <div className="flex flex-col gap-4">
      <div
        data-testid="upload-dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={cn(
          "bg-bg flex min-h-48 flex-col items-center justify-center gap-2 rounded-[1.25rem] border-2 border-dashed p-6 text-center transition-colors",
          dragOver ? "border-accent" : "border-current/30",
        )}
      >
        <ImageIcon className="size-10 opacity-70" aria-hidden="true" />
        <h3 className="text-base font-semibold">Drop photos to upload</h3>
        <p className="text-sm text-ink/70">or choose files from your device</p>
        <Button
          size="md"
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
          accept="image/*,video/*"
          onChange={handleInputChange}
        />
      </div>

      {jobs.length > 0 && (
        <ul className="flex flex-col gap-3" aria-label="Upload queue">
          {jobs.map((job) => (
            <li
              key={job.id}
              data-testid="upload-row"
              className="flex items-start gap-2"
            >
              <div className="bg-bg size-12 shrink-0 rounded-lg" />
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span
                    data-testid="upload-filename"
                    className="min-w-0 flex-1 truncate text-sm"
                  >
                    {job.file.name}
                  </span>
                  <span
                    className={cn(
                      "flex shrink-0 items-center gap-1 text-xs",
                      job.status === "error"
                        ? "text-destructive"
                        : "text-ink/70",
                    )}
                  >
                    {job.status === "uploading" && (
                      <Loader2
                        className="size-4 motion-safe:animate-spin"
                        aria-hidden="true"
                      />
                    )}
                    {job.status === "done" && (
                      <Check className="text-leaf size-4" aria-hidden="true" />
                    )}
                    {job.status === "error" && (
                      <X className="size-4" aria-hidden="true" />
                    )}
                    {job.status === "error"
                      ? job.error || "Error"
                      : job.status === "done"
                        ? "Done"
                        : `${Math.round(job.progress)}%`}
                  </span>
                </div>
                <div
                  role="progressbar"
                  aria-label={`Upload progress for ${job.file.name}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(job.progress)}
                  className="bg-bg h-1 overflow-hidden rounded-full"
                >
                  <div
                    className={cn(
                      "h-full",
                      job.status === "error" ? "bg-destructive" : "bg-accent",
                    )}
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>
              {job.status === "error" && (
                <IconButton
                  data-testid="retry-button"
                  size="sm"
                  variant="ghost"
                  aria-label={`Retry ${job.file.name}`}
                  onClick={() => retry(job.id)}
                >
                  <RotateCw className="size-4" aria-hidden="true" />
                </IconButton>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default GalleryUpload;
