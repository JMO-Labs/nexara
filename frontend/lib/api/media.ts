/**
 * @file lib/api/media.ts
 * @brief Media upload (single + multipart) and metadata.
 *
 * Multipart raw-bytes PUT bypasses apiClient (which JSON-encodes bodies)
 * and uses fetch + bearer-from-session directly.
 */
import { apiGet, apiPost, apiDelete } from "./client";
import { API_BASE, getAccessToken } from "@/lib/auth/session";

export interface MediaItem {
  id: string;
  filename: string;
  content_type: string;
  storage_key: string;
  thumbnail_key: string | null;
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_secs: number | null;
  alt_text: string | null;
  status: "processing" | "ready" | "error";
  created_at: string;
}

export interface MultipartInit {
  upload_id: string;
  part_size: number;
}

const BASE = "/api/v1/media";
const SINGLE_SHOT_LIMIT = 5 * 1024 * 1024;

export const getMedia = (id: string) => apiGet<MediaItem>(`${BASE}/${id}`);
export const deleteMedia = (id: string) => apiDelete<void>(`${BASE}/${id}`);

export async function singleUpload(
  file: File,
  altText?: string,
): Promise<MediaItem> {
  const fd = new FormData();
  fd.append("file", file);
  if (altText) fd.append("alt_text", altText);
  const token = getAccessToken();
  const res = await fetch(`${API_BASE}${BASE}/upload`, {
    method: "POST",
    body: fd,
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return (await res.json()) as MediaItem;
}

export const initMultipart = (
  filename: string,
  content_type: string,
  total_size: number,
) =>
  apiPost<MultipartInit>(`${BASE}/upload/init`, {
    filename,
    content_type,
    total_size,
  });

export async function putPart(
  uploadId: string,
  partNumber: number,
  bytes: Uint8Array,
): Promise<{ part_number: number; etag: string }> {
  const token = getAccessToken();
  const res = await fetch(
    `${API_BASE}${BASE}/upload/${uploadId}/part/${partNumber}`,
    {
      method: "PUT",
      body: bytes as BodyInit,
      credentials: "include",
      headers: {
        "Content-Type": "application/octet-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
  );
  if (!res.ok)
    throw new Error(`Part ${partNumber} upload failed: ${res.status}`);
  return (await res.json()) as { part_number: number; etag: string };
}

export const completeMultipart = (uploadId: string) =>
  apiPost<{ media_id: string }>(`${BASE}/upload/${uploadId}/complete`);

export async function multipartUpload(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<MediaItem> {
  const init = await initMultipart(file.name, file.type, file.size);
  const totalParts = Math.ceil(file.size / init.part_size);
  for (let i = 0; i < totalParts; i++) {
    const start = i * init.part_size;
    const end = Math.min(start + init.part_size, file.size);
    const buf = await file.slice(start, end).arrayBuffer();
    await putPart(init.upload_id, i + 1, new Uint8Array(buf));
    onProgress?.(((i + 1) / totalParts) * 100);
  }
  const result = await completeMultipart(init.upload_id);
  return await getMedia(result.media_id);
}

export async function uploadFile(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<MediaItem> {
  if (file.size <= SINGLE_SHOT_LIMIT) {
    onProgress?.(0);
    const m = await singleUpload(file);
    onProgress?.(100);
    return m;
  }
  return await multipartUpload(file, onProgress);
}
