/**
 * @file tests/unit/hooks/useGalleryUpload.test.ts
 * @brief Gallery upload queue: uploads all files, then one bulk add call.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import * as galleryApi from "@/lib/api/galleries";
import * as mediaApi from "@/lib/api/media";
import { useGalleryUpload } from "@/hooks/useGalleryUpload";
import { qk } from "@/lib/query-keys";

vi.mock("@/lib/api/galleries");
vi.mock("@/lib/api/media");

const media = (id: string) =>
  ({ id, status: "ready" }) as unknown as mediaApi.MediaItem;

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  const hook = renderHook(() => useGalleryUpload("g1"), { wrapper });
  return { ...hook, invalidate };
}

const files = (...names: string[]) =>
  names.map((n) => new File([n], n, { type: "image/jpeg" }));

describe("useGalleryUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(galleryApi.bulkAddItems).mockResolvedValue([]);
  });

  it("uploads 3 files then one bulkAddItems call, no addItem", async () => {
    let n = 0;
    vi.mocked(mediaApi.uploadFile).mockImplementation(async () =>
      media(`m${++n}`),
    );
    const { result, invalidate } = setup();

    await act(() => result.current.enqueue(files("a", "b", "c")));

    expect(mediaApi.uploadFile).toHaveBeenCalledTimes(3);
    expect(galleryApi.addItem).not.toHaveBeenCalled();
    expect(galleryApi.bulkAddItems).toHaveBeenCalledTimes(1);
    const [gid, ids] = vi.mocked(galleryApi.bulkAddItems).mock.calls[0];
    expect(gid).toBe("g1");
    expect([...ids].sort()).toEqual(["m1", "m2", "m3"]);
    expect(result.current.jobs.map((j) => j.status)).toEqual([
      "done",
      "done",
      "done",
    ]);
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: [...qk.galleries.detail("g1"), "items"],
    });
  });

  it("marks failed uploads as error, excludes them from bulk", async () => {
    vi.mocked(mediaApi.uploadFile).mockImplementation(async (f: File) => {
      if (f.name === "bad") throw new Error("Upload failed");
      return media(`id-${f.name}`);
    });
    const { result } = setup();

    await act(() => result.current.enqueue(files("ok1", "bad", "ok2")));

    expect(galleryApi.bulkAddItems).toHaveBeenCalledTimes(1);
    const ids = vi.mocked(galleryApi.bulkAddItems).mock.calls[0][1];
    expect([...ids].sort()).toEqual(["id-ok1", "id-ok2"]);
    const byName = Object.fromEntries(
      result.current.jobs.map((j) => [j.file.name, j]),
    );
    expect(byName.bad.status).toBe("error");
    expect(byName.bad.error).toBe("Upload failed");
    expect(byName.ok1.status).toBe("done");
    expect(byName.ok2.status).toBe("done");
  });

  it("skips bulk call when every upload fails", async () => {
    vi.mocked(mediaApi.uploadFile).mockRejectedValue(new Error("nope"));
    const { result, invalidate } = setup();

    await act(() => result.current.enqueue(files("a", "b")));

    expect(galleryApi.bulkAddItems).not.toHaveBeenCalled();
    expect(invalidate).not.toHaveBeenCalled();
    expect(result.current.jobs.every((j) => j.status === "error")).toBe(true);
  });

  it("marks uploaded jobs as error when the bulk call fails", async () => {
    vi.mocked(mediaApi.uploadFile).mockResolvedValue(media("m1"));
    vi.mocked(galleryApi.bulkAddItems).mockRejectedValue(new Error("bulk"));
    const { result, invalidate } = setup();

    await act(() => result.current.enqueue(files("a")));

    expect(result.current.jobs[0].status).toBe("error");
    expect(result.current.jobs[0].error).toBe("bulk");
    expect(invalidate).not.toHaveBeenCalled();
  });
});
