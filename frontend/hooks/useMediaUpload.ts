/**
 * @file hooks/useMediaUpload.ts
 * @brief Single-file media upload with progress tracking.
 */
"use client";

import { useState, useCallback } from "react";
import { uploadFile } from "@/lib/api/media";
import type { MediaItem } from "@/lib/api/media";

export interface UseMediaUploadResult {
  mutateAsync: (file: File) => Promise<string>;
  isPending: boolean;
  progress: number;
}

export function useMediaUpload(): UseMediaUploadResult {
  const [isPending, setIsPending] = useState(false);
  const [progress, setProgress] = useState(0);

  const mutateAsync = useCallback(async (file: File): Promise<string> => {
    setIsPending(true);
    setProgress(0);

    try {
      const media: MediaItem = await uploadFile(file, (pct: number) => {
        setProgress(pct);
      });
      return media.id;
    } finally {
      setIsPending(false);
      setProgress(0);
    }
  }, []);

  return { mutateAsync, isPending, progress };
}
