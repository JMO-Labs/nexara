/**
 * @file tests/unit/lists/pages/routes.test.tsx
 * @brief App Router modules under app/app/lists: metadata, error, loading.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/components/lists/pages/ListsBrowseView", () => ({ ListsBrowseView: () => <p>browse</p> }));
vi.mock("@/components/lists/pages/ListNewView", () => ({ ListNewView: () => <p>new</p> }));
vi.mock("@/components/lists/pages/ListDetailView", () => ({
  ListDetailView: ({ id }: { id: string }) => <p>detail {id}</p>,
  ListEditView: ({ id }: { id: string }) => <p>edit {id}</p>,
}));
vi.mock("@/components/lists/pages/TemplatesView", () => ({ TemplatesView: () => <p>templates</p> }));
vi.mock("@/components/lists/pages/TemplateDesignerView", () => ({
  TemplateNewView: () => <p>tpl new</p>,
  TemplateEditView: ({ id }: { id: string }) => <p>tpl edit {id}</p>,
}));

import * as browse from "@/app/app/lists/page";
import * as create from "@/app/app/lists/new/page";
import * as detail from "@/app/app/lists/[id]/page";
import * as edit from "@/app/app/lists/[id]/edit/page";
import * as gallery from "@/app/app/lists/templates/page";
import * as tplNew from "@/app/app/lists/templates/new/page";
import * as tplEdit from "@/app/app/lists/templates/[id]/page";
import ErrorPage from "@/app/app/lists/error";
import Loading from "@/app/app/lists/loading";

const params = (id: string) => ({ params: Promise.resolve({ id }) });

const routes = [
  { mod: browse, args: {}, text: "browse", title: "Lists" },
  { mod: create, args: {}, text: "new", title: "New list" },
  { mod: detail, args: params("l1"), text: "detail l1", title: "List" },
  { mod: edit, args: params("l1"), text: "edit l1", title: "Edit list" },
  { mod: gallery, args: {}, text: "templates", title: "List templates" },
  { mod: tplNew, args: {}, text: "tpl new", title: "New template" },
  { mod: tplEdit, args: params("t1"), text: "tpl edit t1", title: "Edit template" },
];

describe("lists routes", () => {
  it.each(routes)("$title page renders and has metadata", async (r) => {
    const md = await r.mod.generateMetadata();
    expect(md.title).toBe(r.title);
    expect(md.description).toBeTruthy();
    expect(md.openGraph).toMatchObject({ title: r.title });
    const el = await r.mod.default(r.args as never);
    render(el);
    expect(screen.getByText(r.text)).toBeInTheDocument();
  });

  it("error boundary shows an error card and retries", async () => {
    const reset = vi.fn();
    render(<ErrorPage error={new Error("boom")} reset={reset} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(reset).toHaveBeenCalled();
  });

  it("loading renders a skeleton", () => {
    render(<Loading />);
    expect(screen.getByTestId("list-page-loading")).toBeInTheDocument();
  });
});
