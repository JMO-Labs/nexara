/**
 * @file tests/unit/subgroups/hub-tabs.test.ts
 * @brief Verify GROUP_TABS has icons and expected structure.
 */
import { describe, it, expect } from "vitest";
import { GROUP_TABS } from "@/components/subgroups/hub/tabs";

describe("GROUP_TABS", () => {
  it("has all required tabs with icons", () => {
    const tabIds = [
      "overview",
      "events",
      "photos",
      "posts",
      "lists",
      "tagged",
      "members",
      "settings",
    ];
    expect(GROUP_TABS).toHaveLength(8);

    GROUP_TABS.forEach((tab) => {
      expect(tabIds).toContain(tab.id);
      expect(tab.label).toBeTruthy();
      expect(tab.Icon).toBeDefined(); // Icon is a React component
    });
  });

  it("merges Galleries and Media into a single Photos tab", () => {
    const ids = GROUP_TABS.map((t) => t.id);
    expect(ids).not.toContain("galleries");
    expect(ids).not.toContain("media");
    const photos = GROUP_TABS.find((t) => t.id === "photos");
    expect(photos?.label).toBe("Photos");
    expect(photos?.Component).toBeDefined();
  });

  it("places lists right after posts", () => {
    const ids = GROUP_TABS.map((t) => t.id);
    expect(ids[ids.indexOf("posts") + 1]).toBe("lists");
  });

  it("settings tab has visible() predicate for role check", () => {
    const settingsTab = GROUP_TABS.find((t) => t.id === "settings");
    expect(settingsTab?.visible).toBeDefined();
  });
});
