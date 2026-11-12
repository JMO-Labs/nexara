/**
 * @file hooks/useGalleryUpload.ts
 * @brief Queue management for gallery bulk uploads. XMLHttpRequest for progress,
 *        Promise pool semaphore (max 5 workers), one bulk add to gallery.
 */
import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useMediaUpload } from "./useMediaUpload";
import { bulkAddItems } from "@/lib/api/galleries";
import { qk } from "@/lib/query-keys";

export interface UploadJob {
  id: string;
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error: string | null;
}

export function useGalleryUpload(galleryId: string) {
  const qc = useQueryClient();
  const mediaUpload = useMediaUpload();
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const maxConcurrency = 5;

  const setStatus = (file: File, patch: Partial<UploadJob>) =>
    setJobs((js) => js.map((j) => (j.file === file ? { ...j, ...patch } : j)));

  /**
   * Upload files with a bounded worker pool, then add all successful media
   * to the gallery with a single bulk call.
   */
  const processBatch = useCallback(
    async (files: File[]) => {
      const pending = [...files];
      const uploaded: { file: File; mediaId: string }[] = [];

      const worker = async () => {
        for (let file = pending.shift(); file; file = pending.shift()) {
          setStatus(file, { status: "uploading" });
          try {
            uploaded.push({
              file,
              mediaId: await mediaUpload.mutateAsync(file),
            });
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            setStatus(file, { status: "error", error: msg });
          }
        }
      };
      await Promise.all(
        Array.from({ length: Math.min(maxConcurrency, files.length) }, worker),
      );
      if (uploaded.length === 0) return;

      try {
        await bulkAddItems(
          galleryId,
          uploaded.map((u) => u.mediaId),
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        uploaded.forEach((u) =>
          setStatus(u.file, { status: "error", error: msg }),
        );
        return;
      }
      uploaded.forEach((u) =>
        setStatus(u.file, { status: "done", progress: 100 }),
      );

      // Refresh items list + gallery detail (item_count) + list view
      qc.invalidateQueries({
        queryKey: [...qk.galleries.detail(galleryId), "items"],
      });
      qc.invalidateQueries({ queryKey: qk.galleries.detail(galleryId) });
      qc.invalidateQueries({ queryKey: qk.galleries.all() });
    },
    [galleryId, qc, mediaUpload],
  );

  const enqueue = useCallback(
    async (files: File[]) => {
      const newJobs: UploadJob[] = files.map((file, idx) => ({
        id: `${Date.now()}-${idx}`,
        file,
        progress: 0,
        status: "pending",
        error: null,
      }));
      setJobs((js) => [...js, ...newJobs]);
      await processBatch(files);
    },
    [processBatch],
  );

  const retry = useCallback(
    async (jobId: string) => {
      const job = jobs.find((j) => j.id === jobId);
      if (!job) return;
      setJobs((js) =>
        js.map((j) =>
          j.id === jobId
            ? { ...j, status: "pending", error: null, progress: 0 }
            : j,
        ),
      );
      await processBatch([job.file]);
    },
    [jobs, processBatch],
  );

  return { jobs, enqueue, retry };
}
