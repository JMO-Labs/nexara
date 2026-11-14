/**
 * @file tests/unit/lists/lists-api.test.ts
 * @brief listApi/templateApi hit the right endpoints and map snake_case to camelCase.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const m = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  ...m,
}));

import { listApi } from "@/lib/api/lists";
import { templateApi } from "@/lib/api/listTemplates";

const rawList = {
  id: "l1",
  title: "T",
  owner_id: "u1",
  item_count: 3,
  completed_count: 1,
  field_schema: [{ key: "a_b" }],
};

beforeEach(() => Object.values(m).forEach((f) => f.mockReset()));

describe("listApi", () => {
  it("getLists maps page and passes cursor", async () => {
    m.apiGet.mockResolvedValue({
      lists: [rawList],
      pagination: { cursor: "c2", has_more: true },
    });
    const r = await listApi.getLists({ cursor: "c1", limit: 10 });
    expect(m.apiGet).toHaveBeenCalledWith("/api/v1/lists?cursor=c1&limit=10");
    expect(r.lists[0]).toMatchObject({ ownerId: "u1", itemCount: 3 });
    expect(r.lists[0].fieldSchema).toEqual([{ key: "a_b" }]);
    expect(r.nextCursor).toBe("c2");
  });
  it("getList maps one list", async () => {
    m.apiGet.mockResolvedValue(rawList);
    expect((await listApi.getList("l1")).completedCount).toBe(1);
    expect(m.apiGet).toHaveBeenCalledWith("/api/v1/lists/l1");
  });
  it("createList sends snake_case body", async () => {
    m.apiPost.mockResolvedValue(rawList);
    await listApi.createList({ title: "T", subgroupId: "s1" });
    expect(m.apiPost).toHaveBeenCalledWith("/api/v1/lists", {
      title: "T",
      subgroup_id: "s1",
    });
  });
  it("updateList uses PUT; delete/archive", async () => {
    m.apiPut.mockResolvedValue(rawList);
    m.apiPost.mockResolvedValue(rawList);
    await listApi.updateList("l1", { expiresAt: "x" });
    expect(m.apiPut).toHaveBeenCalledWith("/api/v1/lists/l1", {
      expires_at: "x",
    });
    await listApi.deleteList("l1");
    expect(m.apiDelete).toHaveBeenCalledWith("/api/v1/lists/l1");
    await listApi.archiveList("l1");
    expect(m.apiPost).toHaveBeenLastCalledWith("/api/v1/lists/l1/archive");
  });
  it("listItems returns nextCursor and items camelCased", async () => {
    m.apiGet.mockResolvedValue({
      items: [{ id: "i1", position: 0, values: { k_x: 1 }, completed_by: "u" }],
      pagination: { cursor: null, has_more: false },
    });
    const r = await listApi.listItems("l1", { cursor: "c" });
    expect(m.apiGet).toHaveBeenCalledWith("/api/v1/lists/l1/items?cursor=c");
    expect(r.items[0].completedBy).toBe("u");
    expect(r.items[0].values).toEqual({ k_x: 1 });
    expect(r.nextCursor).toBeUndefined();
  });
  it("item mutations hit endpoints", async () => {
    m.apiPost.mockResolvedValue({ id: "i1", position: 0 });
    m.apiPut.mockResolvedValue({ id: "i1", position: 0 });
    await listApi.createItem("l1", { position: 0, values: {} });
    expect(m.apiPost).toHaveBeenLastCalledWith("/api/v1/lists/l1/items", {
      position: 0,
      values: {},
    });
    await listApi.updateItem("l1", "i1", { values: { a: 1 } });
    expect(m.apiPut).toHaveBeenCalledWith("/api/v1/lists/l1/items/i1", {
      values: { a: 1 },
    });
    await listApi.deleteItem("l1", "i1");
    expect(m.apiDelete).toHaveBeenCalledWith("/api/v1/lists/l1/items/i1");
    await listApi.completeItem("l1", "i1");
    expect(m.apiPost).toHaveBeenLastCalledWith(
      "/api/v1/lists/l1/items/i1/complete",
    );
    await listApi.uncompleteItem("l1", "i1");
    expect(m.apiPost).toHaveBeenLastCalledWith(
      "/api/v1/lists/l1/items/i1/uncomplete",
    );
  });
  it("signups and members", async () => {
    m.apiPost.mockResolvedValue({ item_id: "i1", user_id: "u", quantity: 2 });
    const s = await listApi.claimSignup("l1", "i1", { quantity: 2 });
    expect(s.itemId).toBe("i1");
    await listApi.releaseSignup("l1", "i1");
    expect(m.apiDelete).toHaveBeenCalledWith(
      "/api/v1/lists/l1/items/i1/signups",
    );
    m.apiPost.mockResolvedValue({
      list_id: "l1",
      user_id: "u",
      share_personal: true,
    });
    const mem = await listApi.addMember("l1", { userId: "u", role: "editor" });
    expect(m.apiPost).toHaveBeenLastCalledWith("/api/v1/lists/l1/members", {
      user_id: "u",
      role: "editor",
    });
    expect(mem.sharePersonal).toBe(true);
    await listApi.removeMember("l1", "u");
    expect(m.apiDelete).toHaveBeenCalledWith("/api/v1/lists/l1/members/u");
  });
  it("getMembers camelizes rows", async () => {
    m.apiGet.mockResolvedValue([
      { list_id: "l1", user_id: "u", share_personal: false },
    ]);
    const rows = await listApi.getMembers("l1");
    expect(m.apiGet).toHaveBeenLastCalledWith("/api/v1/lists/l1/members");
    expect(rows[0].userId).toBe("u");
  });
});

describe("templateApi", () => {
  const raw = {
    id: "t1",
    name: "N",
    is_shared: true,
    fields: [
      {
        id: "f",
        key: "k",
        type_key: "text",
        label: "L",
        required: false,
        position: 0,
      },
    ],
    items: [],
  };
  it("getTemplates maps page", async () => {
    m.apiGet.mockResolvedValue({
      templates: [raw],
      cursor: "n",
      has_more: true,
    });
    const r = await templateApi.getTemplates();
    expect(m.apiGet).toHaveBeenCalledWith("/api/v1/list_templates");
    expect(r.templates[0].isShared).toBe(true);
    expect(r.templates[0].fields[0].typeKey).toBe("text");
    expect(r.nextCursor).toBe("n");
  });
  it("CRUD + clone", async () => {
    m.apiGet.mockResolvedValue(raw);
    expect((await templateApi.getTemplate("t1")).name).toBe("N");
    m.apiPost.mockResolvedValue(raw);
    await templateApi.createTemplate({
      name: "N",
      isShared: true,
      fields: [{ key: "k", label: "L", typeKey: "text", position: 0 }],
    });
    expect(m.apiPost).toHaveBeenCalledWith("/api/v1/list_templates", {
      name: "N",
      is_shared: true,
      fields: [{ key: "k", label: "L", type_key: "text", position: 0 }],
    });
    m.apiPut.mockResolvedValue(raw);
    await templateApi.updateTemplate("t1", { name: "M" });
    expect(m.apiPut).toHaveBeenCalledWith("/api/v1/list_templates/t1", {
      name: "M",
    });
    await templateApi.deleteTemplate("t1");
    expect(m.apiDelete).toHaveBeenCalledWith("/api/v1/list_templates/t1");
    m.apiPost.mockResolvedValue(rawList);
    const l = await templateApi.cloneTemplate("t1", { includeItems: false });
    expect(m.apiPost).toHaveBeenLastCalledWith(
      "/api/v1/list_templates/t1/clone",
      {
        include_items: false,
      },
    );
    expect(l.ownerId).toBe("u1");
  });
});
