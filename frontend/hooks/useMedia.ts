"use client";
/**
 * @file hooks/useMedia.ts
 * @brief Media upload + metadata hooks. No backend list endpoint — recent
 *        uploads tracked in-memory by callers.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useToasts } from "@/stores/toasts";
import { useMutationWithToast } from "./useMutationWithToast";
import * as React from "react";
import { qk } from "@/lib/query-keys";
import {
  getMedia,
  deleteMedia,
  uploadFile,
  type MediaItem,
} from "@/lib/api/media";

export function useMediaDetail(id: string | null | undefined) {
  return useQuery({
    queryKey: ["media", "detail", id ?? ""] as const,
    queryFn: () => getMedia(id as string),
    enabled: !!id,
  });
}

export function useDeleteMedia() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (id: string) => deleteMedia(id),
    successKey: "toasts.media.deleted",
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.media.list() }),
  });
}

export interface UploadState {
  uploading: boolean;
  progress: number;
  error: Error | null;
  upload: (file: File) => Promise<MediaItem>;
}

export function useUpload(): UploadState {
  const t = useTranslations();
  const push = useToasts((s) => s.push);
  const [uploading, setUploading] = React.useState(false);
  const [progress, setProgress] = React.useState(0);
  const [error, setError] = React.useState<Error | null>(null);

  const upload = React.useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      setProgress(0);
      try {
        const result = await uploadFile(file, setProgress);
        push({ variant: "success", message: t("toasts.media.uploaded") });
        return result;
      } catch (e) {
        const err = e instanceof Error ? e : new Error(String(e));
        setError(err);
        const msg =
          (e as unknown as { body?: { error?: { message?: string } } })?.body
            ?.error?.message ?? t("toasts.errors.generic");
        push({ variant: "danger", message: msg });
        throw err;
      } finally {
        setUploading(false);
      }
    },
    [t, push],
  );

  return { uploading, progress, error, upload };
}
