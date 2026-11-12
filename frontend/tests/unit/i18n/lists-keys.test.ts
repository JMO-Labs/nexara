/**
 * @file tests/unit/i18n/lists-keys.test.ts
 * @brief Guards the lists.* i18n namespace: size, required keys, params.
 */
import { describe, expect, it } from "vitest";
import messages from "@/i18n/en-US.json";

type Tree = { [k: string]: string | Tree };
const lists = (messages as unknown as { lists?: Tree }).lists ?? {};

function flatten(t: Tree, p = ""): Record<string, string> {
  return Object.entries(t).reduce<Record<string, string>>((a, [k, v]) => {
    const key = p ? `${p}.${k}` : k;
    return typeof v === "string"
      ? { ...a, [key]: v }
      : { ...a, ...flatten(v, key) };
  }, {});
}
const flat = flatten(lists);

const REQUIRED = [
  "title",
  "create",
  "edit",
  "delete",
  "archive",
  "items.add",
  "items.edit",
  "items.delete",
  "items.complete",
  "items.uncomplete",
  "signups.claim",
  "signups.release",
  "members.add",
  "members.remove",
  "members.share",
  "templates.create",
  "templates.clone",
  "templates.gallery",
  "fields.add",
  "fields.delete",
  "notifications.item",
  "notifications.signup",
  "notifications.completed",
  "notifications.expiring",
  "notifications.member",
  "placeholders.no_lists",
  "placeholders.no_items",
  "placeholders.no_members",
  "messages.created",
  "messages.updated",
  "messages.deleted",
  "messages.error",
];

describe("lists i18n namespace", () => {
  it("has 50+ keys", () => {
    expect(Object.keys(flat).length).toBeGreaterThanOrEqual(50);
  });
  it.each(REQUIRED)("defines lists.%s", (k) => {
    expect(flat[k]).toBeTruthy();
  });
  it("uses ICU single-brace params, never {{ }}", () => {
    for (const v of Object.values(flat)) expect(v).not.toMatch(/\{\{/);
  });
  it("interpolates expected params", () => {
    expect(flat["notifications.item"]).toContain("{listName}");
    expect(flat["notifications.signup"]).toContain("{userName}");
    expect(flat["notifications.member"]).toContain("{inviterName}");
    expect(flat["placeholders.no_items"]).toContain("{listName}");
    expect(flat["actions.confirm_delete"]).toContain("{listName}");
  });
});
