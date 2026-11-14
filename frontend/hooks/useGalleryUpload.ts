/**
 * @file hooks/useGalleryUpload.ts
 * @brief Queue management for gallery bulk uploads. Uploads files with a
 *        Promise pool (max 5 workers), then adds all successful media to the
 *        gallery with one bulk call per batch of up to 100 ids.
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

const MAX_CONCURRENCY = 5;
/** @brief Backend GalleryItemBulkCreate max_length. */
const BULK_LIMIT = 100;

const errMsg = (err: unknown) =>
  err instanceof Error ? err.message : String(err);

/**
 * @brief Gallery upload queue hook.
 * @param galleryId Target gallery.
 * @return jobs list, enqueue(files) and retry(jobId).
 */
export function useGalleryUpload(galleryId: string) {
  const qc = useQueryClient();
  const { mutateAsync: upload } = useMediaUpload();
  const [jobs, setJobs] = useState<UploadJob[]>([]);

  const patch = useCallback(
    (ids: Set<string>, change: Partial<UploadJob>) =>
      setJobs((js) => js.map((j) => (ids.has(j.id) ? { ...j, ...change } : j))),
    [],
  );

  /**
   * @brief Upload the given jobs, then bulk-add the successful media ids.
   * @param batch Jobs to process.
   */
  const run = useCallback(
    async (batch: UploadJob[]) => {
      const uploaded: { jobId: string; mediaId: string }[] = [];
      const queue = [...batch];

      const worker = async () => {
        for (let job = queue.shift(); job; job = queue.shift()) {
          const ids = new Set([job.id]);
          patch(ids, { status: "uploading" });
          try {
            uploaded.push({ jobId: job.id, mediaId: await upload(job.file) });
          } catch (err) {
            patch(ids, { status: "error", error: errMsg(err) });
          }
        }
      };
      await Promise.all(
        Array.from({ length: Math.min(MAX_CONCURRENCY, batch.length) }, worker),
      );
      if (uploaded.length === 0) return;

      // Keep selection order for stable gallery positions.
      const order = new Map(batch.map((j, i) => [j.id, i]));
      uploaded.sort(
        (a, b) => (order.get(a.jobId) ?? 0) - (order.get(b.jobId) ?? 0),
      );

      let added = false;
      for (let i = 0; i < uploaded.length; i += BULK_LIMIT) {
        const chunk = uploaded.slice(i, i + BULK_LIMIT);
        const ids = new Set(chunk.map((u) => u.jobId));
        try {
          await bulkAddItems(
            galleryId,
            chunk.map((u) => u.mediaId),
          );
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
    [galleryId, qc, upload, patch],
  );

  const enqueue = useCallback(
    async (files: File[]) => {
      const stamp = Date.now();
      const newJobs: UploadJob[] = files.map((file, idx) => ({
        id: `${stamp}-${idx}`,
        file,
        progress: 0,
        status: "pending",
        error: null,
      }));
      setJobs((js) => [...js, ...newJobs]);
      await run(newJobs);
    },
    [run],
  );

  const retry = useCallback(
    async (jobId: string) => {
      const job = jobs.find((j) => j.id === jobId);
      if (!job) return;
      patch(new Set([jobId]), { status: "pending", error: null, progress: 0 });
      await run([job]);
    },
    [jobs, run, patch],
  );

  return { jobs, enqueue, retry };
}
