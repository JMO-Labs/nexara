/**
 * @file tests/unit/hooks/useGalleryUpload.test.ts
 * @brief Gallery upload hook uses one bulk call for all uploaded files.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import * as galleriesApi from "@/lib/api/galleries";
import { useGalleryUpload } from "@/hooks/useGalleryUpload";

const uploadMock = vi.fn();
vi.mock("@/hooks/useMediaUpload", () => ({
  useMediaUpload: () => ({ mutateAsync: uploadMock }),
}));
vi.mock("@/lib/api/galleries");

const makeWrapper = (qc: QueryClient) =>
  function W({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };

const files = [1, 2, 3].map(
  (i) => new File(["x"], `f${i}.jpg`, { type: "image/jpeg" }),
);

describe("useGalleryUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(galleriesApi.bulkAddItems).mockResolvedValue([]);
  });

  it("adds all uploaded files with one bulk call", async () => {
    uploadMock.mockImplementation(async (f: File) => `id-${f.name}`);
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, "invalidateQueries");
    const { result } = renderHook(() => useGalleryUpload("g1"), {
      wrapper: makeWrapper(qc),
    });
    await act(async () => {
      await result.current.enqueue(files);
    });
    expect(galleriesApi.bulkAddItems).toHaveBeenCalledTimes(1);
    expect(galleriesApi.bulkAddItems).toHaveBeenCalledWith("g1", [
      "id-f1.jpg",
      "id-f2.jpg",
      "id-f3.jpg",
    ]);
    expect(galleriesApi.addItem).not.toHaveBeenCalled();
    expect(result.current.jobs.every((j) => j.status === "done")).toBe(true);
    expect(spy).toHaveBeenCalled();
  });

  it("marks failed uploads errored and excludes them from bulk", async () => {
    uploadMock.mockImplementation(async (f: File) => {
      if (f.name === "f2.jpg") throw new Error("boom");
      return `id-${f.name}`;
    });
    const qc = new QueryClient();
    const { result } = renderHook(() => useGalleryUpload("g1"), {
      wrapper: makeWrapper(qc),
    });
    await act(async () => {
      await result.current.enqueue(files);
    });
    expect(galleriesApi.bulkAddItems).toHaveBeenCalledWith("g1", [
      "id-f1.jpg",
      "id-f3.jpg",
    ]);
    const bad = result.current.jobs.find((j) => j.file.name === "f2.jpg");
    expect(bad?.status).toBe("error");
    expect(bad?.error).toBe("boom");
  });

  it("skips bulk call and invalidation when nothing uploaded", async () => {
    uploadMock.mockRejectedValue(new Error("x"));
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, "invalidateQueries");
    const { result } = renderHook(() => useGalleryUpload("g1"), {
      wrapper: makeWrapper(qc),
    });
    await act(async () => {
      await result.current.enqueue(files);
    });
    expect(galleriesApi.bulkAddItems).not.toHaveBeenCalled();
    expect(spy).not.toHaveBeenCalled();
  });
});
