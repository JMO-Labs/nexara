/**
 * @file tests/unit/admin/CSSEditor.test.tsx
 * @brief CSSEditor: render, highlight, live preview, byte counter, save.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as api from "@/lib/api/branding";
import { useToasts } from "@/stores/toasts";
import { EditorView } from "@codemirror/view";
import { CSSEditor } from "@/components/admin/CSSEditor";
import { buildPreviewDoc } from "@/components/admin/CSSPreview";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/lib/api/branding", async (orig) => ({
  ...(await orig<typeof api>()),
  updateBranding: vi.fn(),
}));

function wrap(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const editor = () => screen.getByLabelText("Custom CSS");
const view = () => {
  const v = EditorView.findFromDOM(editor());
  if (!v) throw new Error("CodeMirror view not mounted");
  return v;
};
const value = () => view().state.doc.toString();
const type = (v: string) =>
  act(() => {
    view().dispatch({
      changes: { from: 0, to: view().state.doc.length, insert: v },
    });
  });
const preview = () => screen.getByTitle("Live Preview") as HTMLIFrameElement;

beforeEach(() => {
  vi.clearAllMocks();
  useToasts.getState().clear();
});

describe("CSSEditor", () => {
  it("renders editor with initial value, warning and highlighting", () => {
    wrap(<CSSEditor initial="h1 { color: red; }" />);
    expect(editor()).toHaveAttribute("contenteditable", "true");
    expect(editor().closest(".cm-editor")).not.toBeNull();
    expect(value()).toBe("h1 { color: red; }");
    expect(
      screen.getByText(/CSS can break site layout\. Dangerous patterns/),
    ).toBeInTheDocument();
    expect(editor().querySelector(".tok-propertyName")).toHaveTextContent(
      "color",
    );
    expect(editor().querySelector(".tok-typeName")).toHaveTextContent("h1");
  });

  it("updates the sandboxed preview as the user types", () => {
    wrap(<CSSEditor initial="" />);
    expect(screen.getByText("Live Preview")).toBeInTheDocument();
    expect(preview()).toHaveAttribute("sandbox", "");
    type("h1 { color: rebeccapurple; }");
    expect(preview().getAttribute("srcdoc")).toContain(
      "h1 { color: rebeccapurple; }",
    );
  });

  it("neutralises </style> breakouts in the preview", () => {
    wrap(<CSSEditor initial="" />);
    type("</style><script>x</script>");
    expect(preview().getAttribute("srcdoc")).not.toContain("</style><script>");
  });

  it("shows an accurate byte counter and warns above 80%", () => {
    wrap(<CSSEditor initial="" />);
    type("é");
    expect(screen.getByText("2 / 10,240 bytes")).toBeInTheDocument();
    type("a".repeat(8500));
    expect(screen.getByText("8,500 / 10,240 bytes")).toHaveClass(
      "text-destructive",
    );
  });

  it("disables save until dirty and over-limit; reset discards", () => {
    wrap(<CSSEditor initial="a{}" />);
    const save = screen.getByRole("button", { name: /save css/i });
    expect(save).toBeDisabled();
    type("b{}");
    expect(save).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    expect(value()).toBe("a{}");
    type("a".repeat(10241));
    expect(save).toBeDisabled();
  });

  it("saves via the branding mutation and toasts success", async () => {
    vi.mocked(api.updateBranding).mockResolvedValue({
      branding: {} as api.Branding,
    });
    wrap(<CSSEditor initial="" />);
    type("p { margin: 0 }");
    await userEvent.click(screen.getByRole("button", { name: /save css/i }));
    await waitFor(() =>
      expect(vi.mocked(api.updateBranding).mock.calls[0]?.[0]).toEqual({
        custom_css: "p { margin: 0 }",
      }),
    );
    await waitFor(() =>
      expect(useToasts.getState().items.map((t) => t.message)).toContain(
        "Custom CSS saved",
      ),
    );
    expect(screen.getByRole("button", { name: /save css/i })).toBeDisabled();
  });

  it("blocks network fetches from the preview via CSP", () => {
    const doc = buildPreviewDoc("@import url(https://x.test/a.css);");
    expect(doc).toContain('http-equiv="Content-Security-Policy"');
    expect(doc).toContain("default-src 'none'");
  });

  it("toasts an error when saving fails", async () => {
    vi.mocked(api.updateBranding).mockRejectedValue(new Error("boom"));
    wrap(<CSSEditor initial="" />);
    type("p{}");
    await userEvent.click(screen.getByRole("button", { name: /save css/i }));
    await waitFor(() =>
      expect(useToasts.getState().items.map((t) => t.variant)).toContain(
        "danger",
      ),
    );
    expect(screen.getByRole("button", { name: /save css/i })).toBeEnabled();
  });

  it("copies the CSS to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    wrap(<CSSEditor initial="a{}" />);
    fireEvent.click(screen.getByRole("button", { name: /copy/i }));
    expect(writeText).toHaveBeenCalledWith("a{}");
  });
});
