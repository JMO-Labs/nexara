/**
 * @file tests/unit/lists/pages/templateViews.test.tsx
 * @brief /lists/templates, /templates/new, /templates/[id] views.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { TemplateDraft } from "@/lib/lists/templateModel";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) => sel({ user: null }),
}));
vi.mock("@/components/lists/TemplateGallery", () => ({
  TemplateGallery: (p: {
    templates: { id: string; name: string }[];
    onEdit: (t: { id: string }) => void;
    onClone: (t: { id: string }) => void;
  }) => (
    <div>
      {p.templates.map((t) => (
        <span key={t.id}>
          <button onClick={() => p.onEdit(t)}>edit {t.name}</button>
          <button onClick={() => p.onClone(t)}>clone {t.name}</button>
        </span>
      ))}
    </div>
  ),
}));
vi.mock("@/components/lists/TemplateDesigner", () => ({
  TemplateDesigner: (p: {
    initial: TemplateDraft;
    onSave: (d: TemplateDraft) => void;
  }) => (
    <button onClick={() => p.onSave({ ...p.initial, name: "Saved" })}>
      designer {p.initial.name || "empty"}
    </button>
  ),
}));
const h = vi.hoisted(() => ({
  useListTemplates: vi.fn(),
  useListTemplateClone: vi.fn(),
  useListTemplate: vi.fn(),
  useListTemplateCreate: vi.fn(),
  useListTemplateUpdate: vi.fn(),
}));
vi.mock("@/hooks/useLists", () => ({
  useListTemplates: h.useListTemplates,
  useListTemplateClone: h.useListTemplateClone,
}));
vi.mock("@/hooks/useListDetail", () => ({
  useListTemplate: h.useListTemplate,
  useListTemplateCreate: h.useListTemplateCreate,
  useListTemplateUpdate: h.useListTemplateUpdate,
}));

import { TemplatesView } from "@/components/lists/pages/TemplatesView";
import {
  TemplateEditView,
  TemplateNewView,
} from "@/components/lists/pages/TemplateDesignerView";

const apiTpl = {
  id: "t1",
  name: "Potluck",
  isShared: false,
  createdAt: "",
  updatedAt: "",
  fields: [],
  items: [],
};
const mutation = () => {
  const mutate = vi.fn(
    (_v: unknown, o?: { onSuccess?: (r: { id: string }) => void }) =>
      o?.onSuccess?.({ id: "new1" }),
  );
  return { mutate, isPending: false };
};

beforeEach(() => vi.clearAllMocks());

describe("template page views", () => {
  it("gallery lists templates, edits and clones", async () => {
    const clone = mutation();
    h.useListTemplateClone.mockReturnValue(clone);
    h.useListTemplates.mockReturnValue({
      isLoading: false,
      data: { templates: [apiTpl] },
    });
    render(<TemplatesView />);
    expect(screen.getByRole("heading", { name: "Templates" })).toBeVisible();
    expect(screen.getByRole("link", { name: /New template/ })).toHaveAttribute(
      "href",
      "/app/lists/templates/new",
    );
    await userEvent.click(screen.getByText("edit Potluck"));
    expect(push).toHaveBeenCalledWith("/app/lists/templates/t1");
    await userEvent.click(screen.getByText("clone Potluck"));
    expect(clone.mutate.mock.calls[0][0]).toEqual({ id: "t1" });
    expect(push).toHaveBeenCalledWith("/app/lists/new1");
  });

  it("gallery shows loading, error and empty states", () => {
    h.useListTemplateClone.mockReturnValue(mutation());
    h.useListTemplates.mockReturnValue({ isLoading: true });
    const { rerender } = render(<TemplatesView />);
    expect(screen.getByTestId("list-page-loading")).toBeInTheDocument();
    h.useListTemplates.mockReturnValue({
      isLoading: false,
      error: new Error(),
    });
    rerender(<TemplatesView />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    h.useListTemplates.mockReturnValue({
      isLoading: false,
      data: { templates: [] },
    });
    rerender(<TemplatesView />);
    expect(screen.getByText("No templates yet")).toBeInTheDocument();
  });

  it("new view creates a template and returns to the gallery", async () => {
    const create = mutation();
    h.useListTemplateCreate.mockReturnValue(create);
    render(<TemplateNewView />);
    await userEvent.click(screen.getByText("designer empty"));
    expect(create.mutate.mock.calls[0][0]).toEqual({
      name: "Saved",
      fields: [],
    });
    expect(push).toHaveBeenCalledWith("/app/lists/templates");
  });

  it("edit view loads the template and updates it", async () => {
    const update = mutation();
    h.useListTemplateUpdate.mockReturnValue(update);
    h.useListTemplate.mockReturnValue({ isLoading: false, data: apiTpl });
    render(<TemplateEditView id="t1" />);
    expect(h.useListTemplate).toHaveBeenCalledWith("t1");
    await userEvent.click(screen.getByText("designer Potluck"));
    expect(update.mutate.mock.calls[0][0]).toEqual({
      id: "t1",
      data: { name: "Saved", fields: [] },
    });
    expect(push).toHaveBeenCalledWith("/app/lists/templates");
  });

  it("edit view shows loading and error states", () => {
    h.useListTemplateUpdate.mockReturnValue(mutation());
    h.useListTemplate.mockReturnValue({ isLoading: true });
    const { rerender } = render(<TemplateEditView id="t1" />);
    expect(screen.getByTestId("list-page-loading")).toBeInTheDocument();
    h.useListTemplate.mockReturnValue({ isLoading: false, error: new Error() });
    rerender(<TemplateEditView id="t1" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
