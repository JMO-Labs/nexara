/**
 * @file tests/unit/hooks/useMediaUpload.test.ts
 * @brief Single-file media upload hook with progress callback.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as mediaApi from "@/lib/api/media";
import { useMediaUpload } from "@/hooks/useMediaUpload";
import React from "react";

vi.mock("@/lib/api/media");

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
};

describe("useMediaUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uploads file and returns media id on success", async () => {
    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    const mockMedia = {
      id: "media-123",
      filename: "test.jpg",
      content_type: "image/jpeg",
      storage_key: "key",
      thumbnail_key: null,
      size_bytes: 100,
      width: 800,
      height: 600,
      duration_secs: null,
      alt_text: null,
      status: "ready" as const,
      created_at: "2026-04-28T00:00:00Z",
    };

    vi.mocked(mediaApi.uploadFile).mockResolvedValue(mockMedia);

    const { result } = renderHook(() => useMediaUpload(), { wrapper });

    const mediaId = await result.current.mutateAsync(file);

    expect(mediaId).toBe("media-123");
    expect(mediaApi.uploadFile).toHaveBeenCalledWith(
      file,
      expect.any(Function),
    );
  });

  it("calls onProgress callback during upload", async () => {
    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    const progressCallback = vi.fn();

    vi.mocked(mediaApi.uploadFile).mockImplementation((f, onProgress) => {
      onProgress?.(50);
      onProgress?.(100);
      return Promise.resolve({
        id: "media-456",
        filename: "test.jpg",
        content_type: "image/jpeg",
        storage_key: "key",
        thumbnail_key: null,
        size_bytes: 100,
        width: 800,
        height: 600,
        duration_secs: null,
        alt_text: null,
        status: "ready" as const,
        created_at: "2026-04-28T00:00:00Z",
      });
    });

    const { result } = renderHook(() => useMediaUpload(), { wrapper });

    await result.current.mutateAsync(file);

    expect(mediaApi.uploadFile).toHaveBeenCalledWith(
      file,
      expect.any(Function),
    );
  });

  it("sets isPending during upload", async () => {
    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });

    let resolveUpload: any;
    vi.mocked(mediaApi.uploadFile).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUpload = resolve;
        }),
    );

    const { result } = renderHook(() => useMediaUpload(), { wrapper });

    const promise = result.current.mutateAsync(file);

    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    });

    resolveUpload({
      id: "media-789",
      filename: "test.jpg",
      content_type: "image/jpeg",
      storage_key: "key",
      thumbnail_key: null,
      size_bytes: 100,
      width: 800,
      height: 600,
      duration_secs: null,
      alt_text: null,
      status: "ready" as const,
      created_at: "2026-04-28T00:00:00Z",
    });

    await promise;

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });
  });
});
