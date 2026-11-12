/**
 * @file tests/unit/hooks/useGalleryUpload.test.ts
 * @brief Gallery multi-file upload uses one bulk add call.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import * as galleriesApi from "@/lib/api/galleries";
import { useGalleryUpload } from "@/hooks/useGalleryUpload";

const mutateAsync = vi.fn();
vi.mock("@/hooks/useMediaUpload", () => ({
  useMediaUpload: () => ({ mutateAsync }),
}));
vi.mock("@/lib/api/galleries");

const files = ["a", "b", "c"].map(
  (n) => new File([n], `${n}.jpg`, { type: "image/jpeg" }),
);

function setup() {
  const qc = new QueryClient();
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  return { spy, ...renderHook(() => useGalleryUpload("g1"), { wrapper }) };
}

describe("useGalleryUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(galleriesApi.bulkAddItems).mockResolvedValue([]);
  });

  it("uploads 3 files then makes one bulk call and no addItem", async () => {
    mutateAsync.mockImplementation(async (f: File) => `m-${f.name}`);
    const { result, spy } = setup();
    await act(() => result.current.enqueue(files));
    expect(galleriesApi.addItem).not.toHaveBeenCalled();
    expect(galleriesApi.bulkAddItems).toHaveBeenCalledTimes(1);
    expect(galleriesApi.bulkAddItems).toHaveBeenCalledWith("g1", [
      "m-a.jpg",
      "m-b.jpg",
      "m-c.jpg",
    ]);
    expect(result.current.jobs.every((j) => j.status === "done")).toBe(true);
    expect(spy).toHaveBeenCalled();
  });

  it("marks failed uploads errored and excludes them from bulk", async () => {
    mutateAsync.mockImplementation(async (f: File) => {
      if (f.name === "b.jpg") throw new Error("boom");
      return `m-${f.name}`;
    });
    const { result } = setup();
    await act(() => result.current.enqueue(files));
    expect(galleriesApi.bulkAddItems).toHaveBeenCalledWith("g1", [
      "m-a.jpg",
      "m-c.jpg",
    ]);
    const b = result.current.jobs.find((j) => j.file.name === "b.jpg");
    expect(b?.status).toBe("error");
    expect(b?.error).toBe("boom");
  });

  it("skips bulk call when every upload fails", async () => {
    mutateAsync.mockRejectedValue(new Error("x"));
    const { result } = setup();
    await act(() => result.current.enqueue(files));
    expect(galleriesApi.bulkAddItems).not.toHaveBeenCalled();
  });

  it("does not invalidate and marks errors when bulk call fails", async () => {
    mutateAsync.mockImplementation(async (f: File) => `m-${f.name}`);
    vi.mocked(galleriesApi.bulkAddItems).mockRejectedValue(new Error("bad"));
    const { result, spy } = setup();
    await act(() => result.current.enqueue(files));
    expect(result.current.jobs.every((j) => j.status === "error")).toBe(true);
    expect(spy).not.toHaveBeenCalled();
  });
});
