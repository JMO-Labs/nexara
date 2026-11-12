/**
 * @file hooks/useGalleryUpload.ts
 * @brief Queue management for gallery bulk uploads. Uploads files with a
 *        concurrency limit (max 5), then adds all successful media to the
 *        gallery with a single bulk call per batch.
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

const MAX_CONCURRENCY = 5;
/** Backend `GalleryItemBulkCreate.media_ids` max_length. */
const BULK_LIMIT = 100;

let jobSeq = 0;

const errMsg = (err: unknown) =>
  err instanceof Error ? err.message : String(err);

export function useGalleryUpload(galleryId: string) {
  const qc = useQueryClient();
  const mediaUpload = useMediaUpload();
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const inFlightRef = useRef(0);
  const waitersRef = useRef<(() => void)[]>([]);

  const patch = useCallback((ids: string[], p: Partial<UploadJob>) => {
    setJobs((js) => js.map((j) => (ids.includes(j.id) ? { ...j, ...p } : j)));
  }, []);

  /** Acquire a slot in the shared upload pool. */
  const acquire = useCallback(async () => {
    while (inFlightRef.current >= MAX_CONCURRENCY) {
      await new Promise<void>((r) => waitersRef.current.push(r));
    }
    inFlightRef.current++;
  }, []);

  const release = useCallback(() => {
    inFlightRef.current--;
    waitersRef.current.shift()?.();
  }, []);

  /**
   * @brief Upload one job's file.
   * @return Media id on success, null on failure (job marked as error).
   */
  const uploadOne = useCallback(
    async (job: UploadJob): Promise<string | null> => {
      await acquire();
      patch([job.id], { status: "uploading" });
      try {
        return await mediaUpload.mutateAsync(job.file);
      } catch (err) {
        patch([job.id], { status: "error", error: errMsg(err) });
        return null;
      } finally {
        release();
      }
    },
    [acquire, release, patch, mediaUpload],
  );

  /** Upload all jobs, then bulk-add the successful media to the gallery. */
  const process = useCallback(
    async (batch: UploadJob[]) => {
      const results = await Promise.all(batch.map(uploadOne));
      const ok = batch
        .map((job, i) => ({ job, mediaId: results[i] }))
        .filter((r): r is { job: UploadJob; mediaId: string } => !!r.mediaId);
      if (ok.length === 0) return;

      let added = false;
      for (let i = 0; i < ok.length; i += BULK_LIMIT) {
        const chunk = ok.slice(i, i + BULK_LIMIT);
        const ids = chunk.map((r) => r.job.id);
        try {
          await bulkAddItems(galleryId, chunk.map((r) => r.mediaId));
          patch(ids, { status: "done", progress: 100 });
          added = true;
        } catch (err) {
          patch(ids, { status: "error", error: errMsg(err) });
        }
      }
      if (!added) return;

      // Refresh items list + gallery detail (item_count) + list view
      qc.invalidateQueries({
        queryKey: [...qk.galleries.detail(galleryId), "items"],
      });
      qc.invalidateQueries({ queryKey: qk.galleries.detail(galleryId) });
      qc.invalidateQueries({ queryKey: qk.galleries.all() });
    },
    [galleryId, qc, uploadOne, patch],
  );

  const enqueue = useCallback(
    async (files: File[]) => {
      const stamp = Date.now();
      const newJobs: UploadJob[] = files.map((file) => ({
        id: `${stamp}-${jobSeq++}`,
        file,
        progress: 0,
        status: "pending",
        error: null,
      }));
      setJobs((js) => [...js, ...newJobs]);
      await process(newJobs);
    },
    [process],
  );

  const retry = useCallback(
    async (jobId: string) => {
      const job = jobs.find((j) => j.id === jobId);
      if (!job) return;
      const reset: UploadJob = {
        ...job,
        status: "pending",
        error: null,
        progress: 0,
      };
      patch([jobId], reset);
      await process([reset]);
    },
    [jobs, process, patch],
  );

  return { jobs, enqueue, retry };
}
