/**
 * @file tests/unit/admin/sso/GroupMappingEditor.test.tsx
 * @brief group_mapping <-> rows conversion and row removal.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  GroupMappingEditor,
  mappingToRows,
  rowsToMapping,
} from "@/components/admin/sso/GroupMappingEditor";
import { GROUPS } from "./fixtures";

describe("group mapping conversion", () => {
  it("reads single-rule and list values", () => {
    expect(
      mappingToRows({
        ops: { subgroup_id: null, role: "admin" },
        fam: [
          { subgroup_id: "a", role: "member" },
          { subgroup_id: "b", role: "member" },
        ],
      }),
    ).toEqual([
      { group: "ops", role: "admin", subgroupIds: [] },
      { group: "fam", role: "", subgroupIds: ["a", "b"] },
    ]);
  });

  it("drops rows without a group or a target", () => {
    expect(
      rowsToMapping([
        { group: " ", role: "admin", subgroupIds: [] },
        { group: "x", role: "", subgroupIds: [] },
        { group: "y", role: "viewer", subgroupIds: ["a"] },
      ]),
    ).toEqual({
      y: [
        { subgroup_id: null, role: "viewer" },
        { subgroup_id: "a", role: "member" },
      ],
    });
  });
});

describe("GroupMappingEditor", () => {
  it("removes a row with a labelled button", async () => {
    const onChange = vi.fn();
    render(
      <GroupMappingEditor
        rows={[{ group: "smiths", role: "member", subgroupIds: [] }]}
        groups={GROUPS}
        onChange={onChange}
      />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Remove mapping smiths" }),
    );
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
