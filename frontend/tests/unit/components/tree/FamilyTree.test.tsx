/**
 * @file tests/unit/components/tree/FamilyTree.test.tsx
 * @brief FamilyTree: a11y summary, private nodes, list view, friends toggle.
 */
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { FamilyTree, summarize } from "@/components/tree/FamilyTree";
import type { TreeData, TreeNode } from "@/lib/api/tree";

const node = (
  id: string,
  name: string,
  o: Partial<TreeNode> = {},
): TreeNode => ({
  id,
  name,
  avatar_url: null,
  kind: "user",
  memorial: false,
  link: `/app/u/${name.toLowerCase()}`,
  born: null,
  died: null,
  ...o,
});

const data: TreeData = {
  root: "u:1",
  truncated: false,
  nodes: [
    node("u:1", "Dana"),
    node("u:2", "Ruth", {
      memorial: true,
      born: "1930-01-01",
      died: "2020-05-05",
    }),
    node("p:1", "Private relative", { kind: "private", link: null }),
    node("u:4", "Sam"),
    node("u:5", "Loner"),
  ],
  edges: [
    { a: "u:2", b: "u:1", kind: "parent" },
    { a: "p:1", b: "u:1", kind: "parent" },
    { a: "u:1", b: "u:4", kind: "friend" },
  ],
};

describe("FamilyTree", () => {
  it("labels the svg with a summary", () => {
    render(<FamilyTree data={data} />);
    const svg = screen.getByRole("img", { name: /family tree with 5 people/i });
    expect(svg.getAttribute("aria-label")).toBe(summarize(data, 2));
  });

  it("shows private relatives without a link and remembered dates", () => {
    render(<FamilyTree data={data} />);
    expect(screen.getByText("Private relative").closest("a")).toBeNull();
    expect(
      screen.getByRole("link", { name: /Ruth, remembered, 1930 to 2020/ }),
    ).toBeTruthy();
  });

  it("friends toggle moves a friend-only person between linked and unlinked", () => {
    render(<FamilyTree data={data} />);
    expect(
      screen.getByRole("region", { name: "Not linked yet" }).textContent,
    ).toContain("Sam");
    fireEvent.click(screen.getByLabelText("Show friends"));
    expect(
      screen.getByRole("region", { name: "Not linked yet" }).textContent,
    ).not.toContain("Sam");
  });

  it("list view renders nested lists", () => {
    render(<FamilyTree data={data} />);
    fireEvent.click(screen.getByRole("button", { name: /list view/i }));
    const list = screen.getByRole("list", { name: "Family list" });
    expect(list.textContent).toContain("Ruth");
    expect(
      screen.getByRole("list", { name: "Children of Private relative" })
        .textContent,
    ).toContain("Dana");
    expect(screen.queryByRole("img", { name: /family tree/i })).toBeNull();
  });

  it("offers expand only when truncated", () => {
    const { rerender } = render(<FamilyTree data={data} onExpand={() => {}} />);
    expect(
      screen.queryByRole("button", { name: /more relatives/i }),
    ).toBeNull();
    rerender(
      <FamilyTree data={{ ...data, truncated: true }} onExpand={() => {}} />,
    );
    expect(
      screen.getByRole("button", { name: /more relatives/i }),
    ).toBeTruthy();
  });
});
