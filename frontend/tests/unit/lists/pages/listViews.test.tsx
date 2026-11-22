/**
 * @file tests/unit/lists/pages/listViews.test.tsx
 * @brief /lists, /lists/new, /lists/[id], /lists/[id]/edit views.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { list } from "../listFixtures";

const push = vi.fn();
const replace = vi.fn();
let search = new URLSearchParams("type=list");
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  useSearchParams: () => search,
}));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { community_id: "c1" } }),
}));
vi.mock("@/components/ui/Select", () => ({
  Select: (p: {
    label: string;
    value: string;
    onValueChange: (v: string) => void;
    children: React.ReactNode;
  }) => (
    <select
      aria-label={p.label}
      value={p.value}
      onChange={(e) => p.onValueChange(e.target.value)}
    >
      {p.children}
    </select>
  ),
  Option: (p: { value: string; children: React.ReactNode }) => (
    <option value={p.value}>{p.children}</option>
  ),
}));
vi.mock("@/components/lists/ListCardGrid", () => ({
  ListCardGrid: (p: {
    communityId: string;
    visibility?: string;
    sortBy?: string;
    onOpen: (l: { id: string }) => void;
  }) => (
    <button onClick={() => p.onOpen({ id: "l9" })}>
      grid {p.communityId} {p.visibility ?? "all"} {p.sortBy}
    </button>
  ),
}));
vi.mock("@/components/lists/ListCreateForm", () => ({
  ListCreateForm: (p: { onCancel: () => void }) => (
    <button onClick={p.onCancel}>close create</button>
  ),
}));
vi.mock("@/components/lists/ListEditForm", () => ({
  ListEditForm: (p: { onCancel: () => void; list: { title: string } }) => (
    <button onClick={p.onCancel}>close edit {p.list.title}</button>
  ),
}));
vi.mock("@/components/lists/ListDetailPanel", () => ({
  ListDetailPanel: (p: { list: { id: string }; communityId: string }) => (
    <p>
      panel {p.list.id} {p.communityId}
    </p>
  ),
}));
const q = vi.hoisted(() => ({
  useList: vi.fn(),
}));
vi.mock("@/hooks/useListDetail", () => q);

import { ListsBrowseView } from "@/components/lists/pages/ListsBrowseView";
import { ListNewView } from "@/components/lists/pages/ListNewView";
import {
  ListDetailView,
  ListEditView,
} from "@/components/lists/pages/ListDetailView";

beforeEach(() => vi.clearAllMocks());

describe("list page views", () => {
  it("browse view shows filters, grid and links (no redundant root crumb)", async () => {
    render(<ListsBrowseView />);
    expect(screen.getByRole("heading", { name: "Lists" })).toBeVisible();
    expect(screen.queryByRole("navigation", { name: "Breadcrumb" })).toBeNull();
    expect(screen.getByRole("link", { name: /New list/ })).toHaveAttribute(
      "href",
      "/app/lists/new",
    );
    expect(screen.getByRole("link", { name: /Templates/ })).toHaveAttribute(
      "href",
      "/app/lists/templates",
    );
    expect(screen.getByText("grid c1 all updated")).toBeInTheDocument();
    const vis = within(screen.getByRole("radiogroup", { name: "Visibility" }));
    await userEvent.click(vis.getByRole("radio", { name: "Private" }));
    const sort = within(screen.getByRole("radiogroup", { name: "Sort by" }));
    await userEvent.click(sort.getByRole("radio", { name: "Title" }));
    await userEvent.click(screen.getByText("grid c1 private title"));
    expect(push).toHaveBeenCalledWith("/app/lists/l9");
  });

  it("embedded browse view drops its header and keeps the buttons", () => {
    render(<ListsBrowseView embedded />);
    expect(screen.queryByRole("heading", { name: "Lists" })).toBeNull();
    expect(screen.getByRole("link", { name: /New list/ })).toHaveAttribute(
      "href",
      "/app/lists/new",
    );
    expect(screen.getByRole("link", { name: /Templates/ })).toBeVisible();
  });

  it("new view renders the create form inline and returns on cancel", async () => {
    search = new URLSearchParams("type=list");
    render(<ListNewView />);
    await userEvent.click(screen.getByText("close create"));
    expect(push).toHaveBeenCalledWith("/app/inbox?view=lists");
  });

  it("new view without a type offers list, wishlist and template", async () => {
    search = new URLSearchParams();
    render(<ListNewView />);
    expect(
      screen.getByRole("link", { name: /From a template/ }),
    ).toHaveAttribute("href", "/app/lists/templates");
    await userEvent.click(screen.getByRole("button", { name: /Wishlist/ }));
    expect(replace).toHaveBeenCalledWith("/app/lists/new?type=wishlist");
  });

  it("detail view renders loading, error and panel states", () => {
    q.useList.mockReturnValue({ isLoading: true });
    const { rerender } = render(<ListDetailView id="l1" />);
    expect(screen.getByTestId("list-page-loading")).toBeInTheDocument();
    q.useList.mockReturnValue({ isLoading: false, error: new Error("x") });
    rerender(<ListDetailView id="l1" />);
    expect(screen.getByRole("alert")).toHaveTextContent("couldn't load");
    q.useList.mockReturnValue({ isLoading: false, data: list });
    rerender(<ListDetailView id="l1" />);
    expect(q.useList).toHaveBeenCalledWith("c1", "l1");
    expect(screen.getByText("panel l1 c1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Edit/ })).toHaveAttribute(
      "href",
      "/app/lists/l1/edit",
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Camping gear" }),
    ).toBeInTheDocument();
  });

  it("edit view renders the edit form inline and returns to detail", async () => {
    q.useList.mockReturnValue({ isLoading: false, data: list });
    render(<ListEditView id="l1" />);
    await userEvent.click(screen.getByText("close edit Camping gear"));
    expect(push).toHaveBeenCalledWith("/app/lists/l1");
  });

  it("edit view shows loading and error states", () => {
    q.useList.mockReturnValue({ isLoading: true });
    const { rerender } = render(<ListEditView id="l1" />);
    expect(screen.getByTestId("list-page-loading")).toBeInTheDocument();
    q.useList.mockReturnValue({ isLoading: false });
    rerender(<ListEditView id="l1" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
