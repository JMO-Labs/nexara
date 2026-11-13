/**
 * @file tests/unit/lib/notifications-client.test.ts
 * @brief v2 notification + webhook API clients hit the documented endpoints.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import * as client from "@/lib/api/client";
import * as notif from "@/lib/api/notifications";
import * as hooks from "@/lib/api/webhooks";

const ok = { message: "ok" };

describe("notifications v2 client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("GET helpers use expected paths", async () => {
    const get = vi.spyOn(client, "apiGet").mockResolvedValue([] as never);
    await notif.listTypes();
    await notif.listActive();
    await notif.getPreferences();
    expect(get.mock.calls.map((c) => c[0])).toEqual([
      "/api/v1/notifications/types",
      "/api/v1/notifications/active",
      "/api/v1/notifications/preferences",
    ]);
  });

  it("POST helpers use expected paths and bodies", async () => {
    const post = vi.spyOn(client, "apiPost").mockResolvedValue(ok as never);
    await notif.dismissOne("n 1");
    await notif.dismissAll();
    await notif.callAction("n1", "rsvp_yes");
    await notif.snooze("1h");
    expect(post.mock.calls).toEqual([
      ["/api/v1/notifications/n%201/dismiss"],
      ["/api/v1/notifications/dismiss-all"],
      ["/api/v1/notifications/n1/actions/rsvp_yes"],
      ["/api/v1/notifications/snooze", { duration: "1h" }],
    ]);
  });

  it("patchPreferences PATCHes body; clearSnooze DELETEs", async () => {
    const patch = vi.spyOn(client, "apiPatch").mockResolvedValue({} as never);
    const del = vi.spyOn(client, "apiDelete").mockResolvedValue(ok as never);
    await notif.patchPreferences({ dnd_timezone: "Europe/Paris" });
    await notif.clearSnooze();
    expect(patch).toHaveBeenCalledWith("/api/v1/notifications/preferences", {
      dnd_timezone: "Europe/Paris",
    });
    expect(del).toHaveBeenCalledWith("/api/v1/notifications/snooze");
  });
});

describe("webhooks client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("user webhook CRUD", async () => {
    const get = vi.spyOn(client, "apiGet").mockResolvedValue([] as never);
    const post = vi.spyOn(client, "apiPost").mockResolvedValue({} as never);
    const patch = vi.spyOn(client, "apiPatch").mockResolvedValue({} as never);
    const del = vi.spyOn(client, "apiDelete").mockResolvedValue(ok as never);
    await hooks.listWebhooks();
    await hooks.createWebhook({ url: "https://x.io/h", type_keys: ["a"] });
    await hooks.updateWebhook("w1", { enabled: false });
    await hooks.deleteWebhook("w1");
    expect(get).toHaveBeenCalledWith("/api/v1/notifications/webhooks");
    expect(post).toHaveBeenCalledWith("/api/v1/notifications/webhooks", {
      url: "https://x.io/h",
      type_keys: ["a"],
    });
    expect(patch).toHaveBeenCalledWith("/api/v1/notifications/webhooks/w1", {
      enabled: false,
    });
    expect(del).toHaveBeenCalledWith("/api/v1/notifications/webhooks/w1");
  });

  it("community webhooks", async () => {
    const get = vi.spyOn(client, "apiGet").mockResolvedValue([] as never);
    const post = vi.spyOn(client, "apiPost").mockResolvedValue({} as never);
    await hooks.listCommunityWebhooks("c1");
    await hooks.createCommunityWebhook("c1", { url: "https://x.io/h" });
    expect(get).toHaveBeenCalledWith("/api/v1/communities/c1/webhooks");
    expect(post).toHaveBeenCalledWith("/api/v1/communities/c1/webhooks", {
      url: "https://x.io/h",
    });
  });
});
