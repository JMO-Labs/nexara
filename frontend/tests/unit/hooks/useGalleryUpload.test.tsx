/**
 * @file tests/unit/hooks/useGalleryUpload.test.tsx
 * @brief Unit tests for useGalleryUpload (success, progress/state, failure).
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, waitFor } from "@testing-library/react";

import { renderHookWithProviders } from "../../utils/renderWithProviders";
import { useGalleryUpload } from "@/hooks/useGalleryUpload";
import { uploadFile } from "@/lib/api/media";
import { addItem, bulkAddItems } from "@/lib/api/galleries";

vi.mock("@/lib/api/media", () => ({ uploadFile: vi.fn() }));
vi.mock("@/lib/api/galleries", () => ({
  addItem: vi.fn(),
  bulkAddItems: vi.fn(),
}));

const file = (name: string) => new File(["x"], name, { type: "image/jpeg" });

describe("useGalleryUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with no jobs", () => {
    const { result } = renderHookWithProviders(() => useGalleryUpload("g1"));
    expect(result.current.jobs).toEqual([]);
  });

  it("uploads, adds to gallery and marks job done", async () => {
    vi.mocked(uploadFile).mockResolvedValue({ id: "m1" } as never);
    vi.mocked(bulkAddItems).mockResolvedValue([]);
    const { result, queryClient } = renderHookWithProviders(() =>
      useGalleryUpload("g1"),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");

    await act(async () => {
      await result.current.enqueue([file("a.jpg")]);
    });

    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(bulkAddItems).toHaveBeenCalledWith("g1", ["m1"]);
    expect(addItem).not.toHaveBeenCalled();
    expect(result.current.jobs).toHaveLength(1);
    expect(result.current.jobs[0]).toMatchObject({
      status: "done",
      progress: 100,
      error: null,
    });
    expect(spy).toHaveBeenCalled();
  });

  it("moves a job through uploading before done", async () => {
    let resolveUpload!: (v: { id: string }) => void;
    vi.mocked(uploadFile).mockImplementation(
      () => new Promise((r) => (resolveUpload = r as never)),
    );
    vi.mocked(bulkAddItems).mockResolvedValue([]);
    const { result } = renderHookWithProviders(() => useGalleryUpload("g1"));

    let pending!: Promise<void>;
    act(() => {
      pending = result.current.enqueue([file("a.jpg")]);
    });
    await waitFor(() =>
      expect(result.current.jobs[0]?.status).toBe("uploading"),
    );

    await act(async () => {
      resolveUpload({ id: "m1" });
      await pending;
    });
    expect(result.current.jobs[0].status).toBe("done");
  });

  it("marks job as error when upload fails", async () => {
    vi.mocked(uploadFile).mockRejectedValue(new Error("boom"));
    const { result } = renderHookWithProviders(() => useGalleryUpload("g1"));

    await act(async () => {
      await result.current.enqueue([file("a.jpg")]);
    });

    expect(bulkAddItems).not.toHaveBeenCalled();
    expect(result.current.jobs[0]).toMatchObject({
      status: "error",
      error: "boom",
    });
  });

  it("marks job as error when bulk add fails", async () => {
    vi.mocked(uploadFile).mockResolvedValue({ id: "m1" } as never);
    vi.mocked(bulkAddItems).mockRejectedValue(new Error("add failed"));
    const { result } = renderHookWithProviders(() => useGalleryUpload("g1"));

    await act(async () => {
      await result.current.enqueue([file("a.jpg")]);
    });

    expect(result.current.jobs[0]).toMatchObject({
      status: "error",
      error: "add failed",
    });
  });

  it("retry re-uploads a failed job successfully", async () => {
    vi.mocked(uploadFile).mockRejectedValueOnce(new Error("boom"));
    vi.mocked(uploadFile).mockResolvedValueOnce({ id: "m2" } as never);
    vi.mocked(bulkAddItems).mockResolvedValue([]);
    const { result } = renderHookWithProviders(() => useGalleryUpload("g1"));

    await act(async () => {
      await result.current.enqueue([file("a.jpg")]);
    });
    expect(result.current.jobs[0].status).toBe("error");

    await act(async () => {
      await result.current.retry(result.current.jobs[0].id);
    });

    expect(result.current.jobs[0]).toMatchObject({
      status: "done",
      error: null,
    });
    expect(bulkAddItems).toHaveBeenLastCalledWith("g1", ["m2"]);
  });

  it("adds 3 uploaded files with one bulk call and no addItem", async () => {
    vi.mocked(uploadFile).mockImplementation(
      async (f: File) => ({ id: `id-${f.name}` }) as never,
    );
    vi.mocked(bulkAddItems).mockResolvedValue([]);
    const { result, queryClient } = renderHookWithProviders(() =>
      useGalleryUpload("g1"),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");

    await act(async () => {
      await result.current.enqueue([
        file("a.jpg"),
        file("b.jpg"),
        file("c.jpg"),
      ]);
    });

    expect(bulkAddItems).toHaveBeenCalledTimes(1);
    expect(bulkAddItems).toHaveBeenCalledWith("g1", [
      "id-a.jpg",
      "id-b.jpg",
      "id-c.jpg",
    ]);
    expect(addItem).not.toHaveBeenCalled();
    expect(result.current.jobs.every((j) => j.status === "done")).toBe(true);
    expect(spy).toHaveBeenCalledWith({
      queryKey: ["galleries", "detail", "g1", "items"],
    });
  });

  it("errors failed uploads and excludes them from the bulk call", async () => {
    vi.mocked(uploadFile).mockImplementation(async (f: File) => {
      if (f.name === "b.jpg") throw new Error("boom");
      return { id: `id-${f.name}` } as never;
    });
    vi.mocked(bulkAddItems).mockResolvedValue([]);
    const { result } = renderHookWithProviders(() => useGalleryUpload("g1"));

    await act(async () => {
      await result.current.enqueue([
        file("a.jpg"),
        file("b.jpg"),
        file("c.jpg"),
      ]);
    });

    expect(bulkAddItems).toHaveBeenCalledTimes(1);
    expect(bulkAddItems).toHaveBeenCalledWith("g1", ["id-a.jpg", "id-c.jpg"]);
    const bad = result.current.jobs.find((j) => j.file.name === "b.jpg");
    expect(bad).toMatchObject({ status: "error", error: "boom" });
  });

  it("skips invalidation when the bulk call fails", async () => {
    vi.mocked(uploadFile).mockResolvedValue({ id: "m1" } as never);
    vi.mocked(bulkAddItems).mockRejectedValue(new Error("nope"));
    const { result, queryClient } = renderHookWithProviders(() =>
      useGalleryUpload("g1"),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");

    await act(async () => {
      await result.current.enqueue([file("a.jpg")]);
    });

    expect(spy).not.toHaveBeenCalled();
  });
});
