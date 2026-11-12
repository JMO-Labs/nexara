/**
 * @file plugin-loader.test.tsx
 * @brief Tests for PluginRegistry and loadPlugins.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiGet: vi.fn() }));
import { apiGet } from "@/lib/api/client";
import {
  PluginRegistry,
  fetchPluginManifests,
  loadPlugins,
} from "@/lib/plugins/plugin-loader";

const Comp = () => null;
const manifest = (id: string, is_enabled = true) => ({
  id,
  name: id,
  version: "1.0.0",
  is_enabled,
  description: "",
});

describe("PluginRegistry", () => {
  beforeEach(() => PluginRegistry.getInstance().reset());

  it("is a singleton", () => {
    expect(PluginRegistry.getInstance()).toBe(PluginRegistry.getInstance());
  });

  it("stores and returns slot mappings", () => {
    const r = PluginRegistry.getInstance();
    r.registerSlotComponent("sidebar-widget", "a", Comp);
    r.registerSlotComponent("sidebar-widget", "b", Comp);
    r.registerSlotComponent("profile-tab", "a", Comp);
    expect(r.getSlotComponents("sidebar-widget").map((e) => e.pluginId)).toEqual(
      ["a", "b"],
    );
    expect(r.getSlotComponents("profile-tab")).toHaveLength(1);
    expect(r.getSlotComponents("admin-tab")).toEqual([]);
  });

  it("notifies subscribers on register", () => {
    const r = PluginRegistry.getInstance();
    const fn = vi.fn();
    const off = r.subscribe(fn);
    r.registerSlotComponent("sidebar-widget", "a", Comp);
    expect(fn).toHaveBeenCalledTimes(1);
    off();
    r.registerSlotComponent("sidebar-widget", "b", Comp);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe("loadPlugins", () => {
  beforeEach(() => {
    PluginRegistry.getInstance().reset();
    vi.mocked(apiGet).mockReset();
  });

  it("fetchPluginManifests calls GET /plugins", async () => {
    vi.mocked(apiGet).mockResolvedValue([manifest("a")]);
    expect(await fetchPluginManifests()).toHaveLength(1);
    expect(apiGet).toHaveBeenCalledWith("/plugins");
  });

  it("imports enabled plugins and calls registerPlugin", async () => {
    vi.mocked(apiGet).mockResolvedValue([manifest("a"), manifest("off", false)]);
    const importer = vi.fn(async (_id: string) => ({
      registerPlugin: (r: PluginRegistry) =>
        r.registerSlotComponent("sidebar-widget", "a", Comp),
    }));
    await loadPlugins(importer);
    expect(importer).toHaveBeenCalledTimes(1);
    expect(importer).toHaveBeenCalledWith("a");
    expect(
      PluginRegistry.getInstance().getSlotComponents("sidebar-widget"),
    ).toHaveLength(1);
  });

  it("skips plugins whose import fails or lack registerPlugin", async () => {
    vi.mocked(apiGet).mockResolvedValue([manifest("bad"), manifest("none"), manifest("ok")]);
    const importer = vi.fn(async (id: string) => {
      if (id === "bad") throw new Error("nope");
      if (id === "none") return {};
      return {
        registerPlugin: (r: PluginRegistry) =>
          r.registerSlotComponent("post-action", "ok", Comp),
      };
    });
    vi.spyOn(console, "error").mockImplementation(() => {});
    await loadPlugins(importer);
    expect(PluginRegistry.getInstance().getSlotComponents("post-action")).toHaveLength(1);
  });

  it("does not throw when manifest fetch fails", async () => {
    vi.mocked(apiGet).mockRejectedValue(new Error("down"));
    vi.spyOn(console, "error").mockImplementation(() => {});
    await expect(loadPlugins(vi.fn())).resolves.toBeUndefined();
  });
});
