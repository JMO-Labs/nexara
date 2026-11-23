/**
 * @file tests/unit/lib/trips-api.test.ts
 * @brief Trips client hits the versioned API paths.
 */
import { describe, expect, it, vi } from "vitest";

const m = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  ...m,
}));

import {
  arriveTrip,
  cancelTrip,
  extendTrip,
  getActiveTrip,
  listWatching,
  startTrip,
} from "@/lib/api/trips";

describe("trips api paths", () => {
  it("all start with /api/v1/trips", () => {
    startTrip({ label: "x", expected_at: "t", watcher_ids: ["a"] });
    getActiveTrip();
    listWatching();
    arriveTrip("t1");
    extendTrip("t1", "t");
    cancelTrip("t1");
    const paths = [
      m.apiPost.mock.calls[0][0],
      m.apiGet.mock.calls[0][0],
      m.apiGet.mock.calls[1][0],
      m.apiPost.mock.calls[1][0],
      m.apiPost.mock.calls[2][0],
      m.apiDelete.mock.calls[0][0],
    ];
    expect(paths).toEqual([
      "/api/v1/trips",
      "/api/v1/trips/active",
      "/api/v1/trips/watching",
      "/api/v1/trips/t1/arrive",
      "/api/v1/trips/t1/extend",
      "/api/v1/trips/t1",
    ]);
  });
});
