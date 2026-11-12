/**
 * @file tests/unit/components/settings/AppriseList.test.tsx
 * @brief AppriseList: list render, test button, edit/delete actions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import en from "@/i18n/en-US.json";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) =>
    (en.settings.apprise as Record<string, string>)[k] ?? k,
}));

const api = vi.hoisted(() => ({
  listAppriseUrls: vi.fn(),
  testAppriseUrl: vi.fn(),
  deleteAppriseUrl: vi.fn(),
  updateAppriseUrl: vi.fn(),
  createAppriseUrl: vi.fn(),
}));
vi.mock("@/lib/api/apprise", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/apprise")>()),
  ...api,
}));
const push = vi.hoisted(() => vi.fn());
vi.mock("@/stores/toasts", () => ({
  useToasts: Object.assign(() => ({}), { getState: () => ({ push }) }),
}));

import { AppriseList } from "@/components/settings/AppriseList";
import { serviceFromUrl } from "@/lib/api/apprise";

const ITEMS = [
  { id: "a1", label: "Team Slack", service: "slack", enabled: true },
  { id: "a2", label: "Phone", service: "tgram", enabled: false },
];

function renderList() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AppriseList />
    </QueryClientProvider>,
  );
}

describe("AppriseList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listAppriseUrls.mockResolvedValue(ITEMS);
  });

  it("renders labels and actions without URL content", async () => {
    renderList();
    expect(await screen.findByText("Team Slack")).toBeInTheDocument();
    expect(screen.getByText("Phone")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /send test.*team slack/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: /enable team slack/i }),
    ).toBeChecked();
  });

  it("test button calls API and toasts status/message", async () => {
    api.testAppriseUrl.mockResolvedValue({ status: "ok", message: "Sent" });
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: /send test.*team slack/i }),
    );
    expect(api.testAppriseUrl).toHaveBeenCalledWith("a1");
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        expect.objectContaining({ variant: "success", message: "Sent" }),
      ),
    );
  });

  it("delete confirms then calls API", async () => {
    api.deleteAppriseUrl.mockResolvedValue(undefined);
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: /delete team slack/i }),
    );
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await waitFor(() =>
      expect(api.deleteAppriseUrl).toHaveBeenCalledWith("a1"),
    );
  });

  it("edit opens the modal with the label", async () => {
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: /edit team slack/i }),
    );
    expect(await screen.findByLabelText(/label/i)).toHaveValue("Team Slack");
  });

  it("shows a service icon from the scheme with Bell fallback", async () => {
    api.listAppriseUrls.mockResolvedValue([
      ...ITEMS,
      { id: "a3", label: "Odd", service: "zzz", enabled: true },
    ]);
    const { container } = renderList();
    await screen.findByText("Team Slack");
    const svc = (s: string) =>
      container.querySelector(`[data-service="${s}"]`) as SVGElement;
    expect(svc("slack")).toBeInTheDocument();
    expect(svc("slack").getAttribute("class")).toContain(
      "lucide-message-circle",
    );
    expect(svc("tgram").getAttribute("class")).toContain("lucide-send");
    expect(svc("zzz").getAttribute("class")).toContain("lucide-bell");
  });

  it("toasts when toggle or delete fails", async () => {
    api.updateAppriseUrl.mockRejectedValue(new Error("x"));
    api.deleteAppriseUrl.mockRejectedValue(new Error("x"));
    renderList();
    await userEvent.click(
      await screen.findByRole("switch", { name: /enable team slack/i }),
    );
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        expect.objectContaining({ variant: "danger" }),
      ),
    );
    push.mockClear();
    await userEvent.click(
      screen.getByRole("button", { name: /delete team slack/i }),
    );
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        expect.objectContaining({ variant: "danger" }),
      ),
    );
  });

  it("create path: save, confirm test, calls create and test", async () => {
    api.createAppriseUrl.mockResolvedValue({ id: "n1" });
    api.testAppriseUrl.mockResolvedValue({ status: "ok", message: "Sent" });
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: /add url/i }),
    );
    await userEvent.type(screen.getByLabelText(/^url/i), "slack://a/b/c");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await userEvent.click(
      await screen.findByRole("button", { name: /save and test/i }),
    );
    await waitFor(() => expect(api.createAppriseUrl).toHaveBeenCalled());
    await waitFor(() => expect(api.testAppriseUrl).toHaveBeenCalledWith("n1"));
  });

  it("shows an error and returns to form when create rejects", async () => {
    api.createAppriseUrl.mockRejectedValue(new Error("400"));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: /add url/i }),
    );
    await userEvent.type(screen.getByLabelText(/^url/i), "slack://a/b/c");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await userEvent.click(
      await screen.findByRole("button", { name: /just save/i }),
    );
    expect(
      await screen.findByText(en.settings.apprise.save_failed),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^url/i)).toBeInTheDocument();
  });

  it("add opens modal and rejects invalid URL", async () => {
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: /add url/i }),
    );
    await userEvent.type(screen.getByLabelText(/^url/i), "not a url");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));
    expect(await screen.findByText("Invalid Apprise URL")).toBeInTheDocument();
    expect(api.createAppriseUrl).not.toHaveBeenCalled();
  });
});

describe("serviceFromUrl", () => {
  it("parses scheme", () => {
    expect(serviceFromUrl("slack://a/b/c")).toBe("slack");
    expect(serviceFromUrl("garbage")).toBeNull();
  });
});
