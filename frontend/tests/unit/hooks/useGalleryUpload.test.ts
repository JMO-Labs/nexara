/**
 * @file tests/unit/hooks/useGalleryUpload.test.ts
 * @brief Uploads all files, then adds successes with one bulk call.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGalleryUpload } from "@/hooks/useGalleryUpload";
import * as galleryApi from "@/lib/api/galleries";
import * as mediaApi from "@/lib/api/media";
import { qk } from "@/lib/query-keys";

vi.mock("@/lib/api/galleries");
vi.mock("@/lib/api/media");

const media = (id: string) =>
  ({ id }) as unknown as Awaited<ReturnType<typeof mediaApi.uploadFile>>;

function setup() {
  const qc = new QueryClient();
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  const hook = renderHook(() => useGalleryUpload("g1"), { wrapper });
  return { hook, spy };
}

const files = ["a", "b", "c"].map(
  (n) => new File([n], `${n}.jpg`, { type: "image/jpeg" }),
);

describe("useGalleryUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(galleryApi.bulkAddItems).mockResolvedValue([]);
  });

  it("uploads 3 files then calls bulkAddItems once", async () => {
    vi.mocked(mediaApi.uploadFile).mockImplementation(async (f: File) =>
      media(`m-${f.name}`),
    );
    const { hook, spy } = setup();

    await act(() => hook.result.current.enqueue(files));

    expect(mediaApi.uploadFile).toHaveBeenCalledTimes(3);
    expect(galleryApi.addItem).not.toHaveBeenCalled();
    expect(galleryApi.bulkAddItems).toHaveBeenCalledTimes(1);
    expect(galleryApi.bulkAddItems).toHaveBeenCalledWith("g1", [
      "m-a.jpg",
      "m-b.jpg",
      "m-c.jpg",
    ]);
    expect(hook.result.current.jobs.map((j) => j.status)).toEqual([
      "done",
      "done",
      "done",
    ]);
    expect(spy).toHaveBeenCalledWith({
      queryKey: [...qk.galleries.detail("g1"), "items"],
    });
  });

  it("marks failed uploads as error and excludes them from bulk", async () => {
    vi.mocked(mediaApi.uploadFile).mockImplementation(async (f: File) => {
      if (f.name === "b.jpg") throw new Error("boom");
      return media(`m-${f.name}`);
    });
    const { hook } = setup();

    await act(() => hook.result.current.enqueue(files));

    expect(galleryApi.bulkAddItems).toHaveBeenCalledTimes(1);
    expect(galleryApi.bulkAddItems).toHaveBeenCalledWith("g1", [
      "m-a.jpg",
      "m-c.jpg",
    ]);
    const jobs = hook.result.current.jobs;
    expect(jobs[1]).toMatchObject({ status: "error", error: "boom" });
    expect(jobs[0].status).toBe("done");
    expect(jobs[2].status).toBe("done");
  });

  it("skips bulk call when all uploads fail", async () => {
    vi.mocked(mediaApi.uploadFile).mockRejectedValue(new Error("x"));
    const { hook, spy } = setup();

    await act(() => hook.result.current.enqueue(files));

    expect(galleryApi.bulkAddItems).not.toHaveBeenCalled();
    expect(spy).not.toHaveBeenCalled();
    expect(hook.result.current.jobs.every((j) => j.status === "error")).toBe(
      true,
    );
  });

  it("marks uploaded files as error when the bulk call fails", async () => {
    vi.mocked(mediaApi.uploadFile).mockImplementation(async (f: File) =>
      media(`m-${f.name}`),
    );
    vi.mocked(galleryApi.bulkAddItems).mockRejectedValue(new Error("denied"));
    const { hook } = setup();

    await act(() => hook.result.current.enqueue(files));

    expect(hook.result.current.jobs.map((j) => j.error)).toEqual([
      "denied",
      "denied",
      "denied",
    ]);
  });
});
