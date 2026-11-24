import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const apiPost = vi.fn();
const apiGet = vi.fn().mockResolvedValue({ id: "m1" });
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiPost: (...a: unknown[]) => apiPost(...a),
  apiGet: (...a: unknown[]) => apiGet(...a),
}));

import { uploadFile } from "@/lib/api/media";

describe("uploadFile multipart", () => {
  beforeEach(() => {
    apiPost.mockReset();
    apiPost.mockImplementation((url: string) =>
      url.endsWith("/upload/init")
        ? Promise.resolve({ upload_id: "u1", part_size: 4 * 1024 * 1024 })
        : Promise.resolve({ media_id: "m1" }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ part_number: 1, etag: "e" }),
      }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  const big = () =>
    new File([new Uint8Array(6 * 1024 * 1024)], "big.jpg", {
      type: "image/jpeg",
    });

  it("forwards the NSFW flag on complete", async () => {
    await uploadFile(big(), undefined, true);
    expect(apiPost).toHaveBeenLastCalledWith(
      "/api/v1/media/upload/u1/complete?is_nsfw=true",
    );
  });

  it("omits the flag when not NSFW", async () => {
    await uploadFile(big());
    expect(apiPost).toHaveBeenLastCalledWith(
      "/api/v1/media/upload/u1/complete",
    );
  });
});
