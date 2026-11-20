/**
 * @file tests/unit/lib/mediaUrl.test.ts
 * @brief mediaThumbUrl picks thumbnail or original file.
 */
import { describe, it, expect } from "vitest";
import { mediaThumbUrl } from "@/lib/mediaUrl";

describe("mediaThumbUrl", () => {
  it("uses the thumbnail when a key exists", () => {
    expect(mediaThumbUrl({ id: "m1", thumbnail_key: "t/m1" })).toBe(
      "/api/v1/media/m1/thumbnail",
    );
  });
  it("falls back to the file", () => {
    expect(mediaThumbUrl({ id: "m1", thumbnail_key: null })).toBe(
      "/api/v1/media/m1/file",
    );
  });
});
