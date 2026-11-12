/**
 * @file hooks/useGalleryUpload.ts
 * @brief Queue management for gallery bulk uploads. XMLHttpRequest for progress,
 *        Promise pool semaphore (max 5 workers), one bulk call to add items.
 */
import { useState, useCallback, useRef } from "react";
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

const BULK_MAX = 100;

export function useGalleryUpload(galleryId: string) {
  const qc = useQueryClient();
  const mediaUpload = useMediaUpload();
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const queueRef = useRef<File[]>([]);
  const inFlightRef = useRef(0);
  const maxConcurrency = 5;
  const drainingRef = useRef(false);

  /**
   * Add uploaded media to the gallery with bulk calls (backend max 100 each).
   */
  const addToGallery = useCallback(
    async (uploaded: { file: File; mediaId: string }[]) => {
      let added = false;
      for (let i = 0; i < uploaded.length; i += BULK_MAX) {
        const chunk = uploaded.slice(i, i + BULK_MAX);
        try {
          await bulkAddItems(
            galleryId,
            chunk.map((u) => u.mediaId),
          );
          added = true;
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          const files = new Set(chunk.map((u) => u.file));
          setJobs((js) =>
            js.map((j) =>
              files.has(j.file) ? { ...j, status: "error", error: msg } : j,
            ),
          );
        }
      }
      if (added) {
        // Refresh items list + gallery detail (item_count) + list view
        qc.invalidateQueries({
          queryKey: [...qk.galleries.detail(galleryId), "items"],
        });
        qc.invalidateQueries({ queryKey: qk.galleries.detail(galleryId) });
        qc.invalidateQueries({ queryKey: qk.galleries.all() });
      }
    },
    [galleryId, qc],
  );

  /**
   * Drain the queue: start uploads up to max concurrency.
   */
  const drainQueue = useCallback(async () => {
    if (drainingRef.current) return;
    drainingRef.current = true;
    const succeeded: { file: File; mediaId: string }[] = [];

    try {
      while (
        queueRef.current.length > 0 &&
        inFlightRef.current < maxConcurrency
      ) {
        const file = queueRef.current.shift();
        if (!file) break;

        inFlightRef.current++;

        setJobs((js) =>
          js.map((j) =>
            j.file === file && j.status === "pending"
              ? { ...j, status: "uploading" }
              : j,
          ),
        );

        try {
          const mediaId = await mediaUpload.mutateAsync(file);
          succeeded.push({ file, mediaId });
          setJobs((js) =>
            js.map((j) =>
              j.file === file ? { ...j, status: "done", progress: 100 } : j,
            ),
          );
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          setJobs((js) =>
            js.map((j) =>
              j.file === file ? { ...j, status: "error", error: msg } : j,
            ),
          );
        } finally {
          inFlightRef.current--;
        }
      }

      await addToGallery(succeeded);
    } finally {
      drainingRef.current = false;
    }
  }, [addToGallery, galleryId, qc, mediaUpload]);

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
      queueRef.current.push(...files);
      await drainQueue();
    },
    [drainQueue],
  );

  const retry = useCallback(
    async (jobId: string) => {
      const job = jobs.find((j) => j.id === jobId);
      if (!job) return;

      // Reset to pending and push back to queue
      setJobs((js) =>
        js.map((j) =>
          j.id === jobId
            ? { ...j, status: "pending", error: null, progress: 0 }
            : j,
        ),
      );

      queueRef.current.unshift(job.file);
      await drainQueue();
    },
    [jobs, drainQueue],
  );

  return { jobs, enqueue, retry };
}
