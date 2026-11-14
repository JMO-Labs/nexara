/**
 * @file tests/unit/lists/templateAdapter.test.ts
 * @brief API <-> designer model conversion for list templates.
 */
import { describe, it, expect } from "vitest";
import { fromApi, toInput } from "@/lib/lists/templateAdapter";
import type { ListTemplate as ApiTemplate } from "@/lib/api/listTypes";

const api: ApiTemplate = {
  id: "t1",
  name: "Potluck",
  isShared: true,
  createdAt: "",
  updatedAt: "",
  items: [],
  fields: [
    { key: "b", label: "B", typeKey: "bool", position: 1 },
    { id: "f1", key: "a", label: "A", typeKey: "text", position: 0, config: { max: 3 } },
  ],
};

describe("templateAdapter", () => {
  it("fromApi maps typeKey, sorts by position and fills ids/config", () => {
    const t = fromApi(api);
    expect(t.id).toBe("t1");
    expect(t.system).toBe(true);
    expect(t.fields.map((f) => f.key)).toEqual(["a", "b"]);
    expect(t.fields[0]).toMatchObject({
      id: "f1",
      type_key: "text",
      config: { max: 3 },
    });
    expect(t.fields[1].id).toBe("b");
    expect(t.fields[1].config).toEqual({});
  });

  it("toInput maps a draft back to the API shape with positions", () => {
    const input = toInput({
      name: "X",
      fields: [
        { id: "z", key: "k", label: "K", type_key: "text", config: {}, position: 4 },
      ],
    });
    expect(input).toEqual({
      name: "X",
      fields: [{ key: "k", label: "K", typeKey: "text", config: {}, position: 0 }],
    });
  });
});
