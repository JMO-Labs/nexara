/**
 * @file tests/unit/admin/sso/GroupMappingEditor.test.tsx
 * @brief group_mapping <-> rows round-trip (no silent role changes) and row editing.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  GroupMappingEditor,
  mappingToRows,
  rowsToMapping,
  type MappingRow,
} from "@/components/admin/sso/GroupMappingEditor";
import type { GroupRule } from "@/lib/api/adminOauth";
import { GROUPS } from "./fixtures";

const STORED: Record<string, GroupRule | GroupRule[]> = {
  ops: { subgroup_id: null, role: "admin" },
  single: { subgroup_id: "g-club", role: "moderator" },
  fam: [
    { subgroup_id: "g-smith", role: "member" },
    { subgroup_id: null, role: "admin" },
  ],
  lead: [
    { subgroup_id: "g-smith", role: "owner" },
    { subgroup_id: "g-club", role: "moderator" },
    { subgroup_id: null, role: "viewer" },
    { subgroup_id: null, role: "member" },
  ],
  gone: [{ subgroup_id: "deleted-group", role: "owner" }],
};

describe("group mapping round-trip", () => {
  it("rowsToMapping(mappingToRows(x)) is the identity", () => {
    expect(rowsToMapping(mappingToRows(STORED))).toEqual(STORED);
  });

  it("drops rows without a group or rules", () => {
    expect(
      rowsToMapping([
        {
          group: " ",
          rules: [{ subgroup_id: null, role: "admin" }],
          list: true,
        },
        { group: "x", rules: [], list: true },
      ]),
    ).toEqual({});
  });

  it("editing an unrelated row keeps owner/moderator and every role", async () => {
    let rows: MappingRow[] = mappingToRows(STORED);
    const onChange = vi.fn((r: MappingRow[]) => (rows = r));
    render(
      <GroupMappingEditor rows={rows} groups={GROUPS} onChange={onChange} />,
    );
    const ops = screen.getByRole("group", { name: "Mapping for ops" });
    await userEvent.type(within(ops).getByLabelText("Provider group"), "2");
    const out = rowsToMapping(rows);
    expect(out.ops2).toEqual(STORED.ops);
    for (const k of ["single", "fam", "lead", "gone"]) {
      expect(out[k]).toEqual(STORED[k]);
    }
  });
});

describe("GroupMappingEditor", () => {
  const setup = (rows: MappingRow[]) => {
    const onChange = vi.fn();
    render(
      <GroupMappingEditor rows={rows} groups={GROUPS} onChange={onChange} />,
    );
    return onChange;
  };

  it("shows the stored subgroup role and the highest community role", () => {
    setup(mappingToRows({ lead: STORED.lead, gone: STORED.gone }));
    const row = screen.getByRole("group", { name: "Mapping for lead" });
    expect(
      (within(row).getByLabelText("Role") as HTMLSelectElement).value,
    ).toBe("member");
    expect(
      (within(row).getByLabelText("Role in Smith Family") as HTMLSelectElement)
        .value,
    ).toBe("owner");
    const gone = screen.getByRole("group", { name: "Mapping for gone" });
    expect(within(gone).getByText(/no longer exist/i)).toBeTruthy();
  });

  it("changing a subgroup role keeps its position", async () => {
    const onChange = setup(mappingToRows({ fam: STORED.fam }));
    await userEvent.selectOptions(
      screen.getByLabelText("Role in Smith Family"),
      "moderator",
    );
    expect(onChange.mock.calls[0][0][0].rules).toEqual([
      { subgroup_id: "g-smith", role: "moderator" },
      { subgroup_id: null, role: "admin" },
    ]);
  });

  it("removes a row with a labelled button", async () => {
    const onChange = setup([
      {
        group: "smiths",
        rules: [{ subgroup_id: null, role: "member" }],
        list: true,
      },
    ]);
    await userEvent.click(
      screen.getByRole("button", { name: "Remove mapping smiths" }),
    );
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
