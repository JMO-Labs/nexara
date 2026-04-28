/**
 * @file hooks/useGalleryUpload.ts
 * @brief Queue management for gallery bulk uploads. XMLHttpRequest for progress,
 *        Promise pool semaphore (max 5 workers), auto-add items to gallery.
 */
import { useState, useCallback, useRef } from 'react';
import { uploadFile } from '@/lib/api/media';
import { addItem } from '@/lib/api/galleries';

export interface UploadJob {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error: string | null;
}

export function useGalleryUpload(galleryId: string) {
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const queueRef = useRef<File[]>([]);
  const inFlightRef = useRef(0);
  const maxConcurrency = 5;
  const drainingRef = useRef(false);

  /**
   * Drain the queue: start uploads up to max concurrency.
   */
  const drainQueue = useCallback(async () => {
    if (drainingRef.current) return;
    drainingRef.current = true;

    try {
      while (queueRef.current.length > 0 && inFlightRef.current < maxConcurrency) {
        const file = queueRef.current.shift();
        if (!file) break;

        inFlightRef.current++;

        setJobs((js) =>
          js.map((j) =>
            j.file === file && j.status === 'pending' ? { ...j, status: 'uploading' } : j,
          ),
        );

        try {
          const media = await uploadFile(file, (pct: number) => {
            setJobs((js) =>
              js.map((j) =>
                j.file === file ? { ...j, progress: pct } : j,
              ),
            );
          });

          // Add to gallery
          await addItem(galleryId, media.id);

          setJobs((js) =>
            js.map((j) =>
              j.file === file ? { ...j, status: 'done', progress: 100 } : j,
            ),
          );
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          setJobs((js) =>
            js.map((j) =>
              j.file === file ? { ...j, status: 'error', error: msg } : j,
            ),
          );
        } finally {
          inFlightRef.current--;
        }
      }
    } finally {
      drainingRef.current = false;
    }
  }, [galleryId]);

  const enqueue = useCallback(
    async (files: File[]) => {
      const newJobs: UploadJob[] = files.map((file, idx) => ({
        id: `${Date.now()}-${idx}`,
        file,
        progress: 0,
        status: 'pending',
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
          j.id === jobId ? { ...j, status: 'pending', error: null, progress: 0 } : j,
        ),
      );

      queueRef.current.unshift(job.file);
      await drainQueue();
    },
    [jobs, drainQueue],
  );

  return { jobs, enqueue, retry };
}
