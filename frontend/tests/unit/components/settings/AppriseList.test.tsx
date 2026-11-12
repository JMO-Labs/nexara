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
