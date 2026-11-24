/**
 * @file tests/unit/components/admin/AuditLogTab.test.tsx
 * @brief Audit log: labels, relative time, states, filters, paging and CSV export.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "../../../utils/renderWithProviders";

vi.mock("@/lib/api/auditLog", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/auditLog")>()),
  listAudit: vi.fn(),
  exportAuditCsv: vi.fn(),
}));
import * as api from "@/lib/api/auditLog";
import { AuditLogTab } from "@/components/admin/AuditLogTab";

const entry = {
  id: "a1",
  action: "invite.created",
  actor_display_name: "Rosa",
  target_type: "invite",
  target_display: null,
  created_at: new Date(Date.now() - 5 * 60_000).toISOString(),
};
const page = (items = [entry], next_cursor: string | null = null) => ({
  items,
  next_cursor,
  has_more: next_cursor !== null,
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listAudit).mockResolvedValue(page() as never);
  URL.createObjectURL = vi.fn(() => "blob:x");
  URL.revokeObjectURL = vi.fn();
});

describe("AuditLogTab", () => {
  it("shows the action as a sentence-case label", async () => {
    render(<AuditLogTab />);
    expect(await screen.findByText("Invite created")).toBeInTheDocument();
    expect(screen.queryByText("invite.created")).toBeNull();
  });

  it("shows a relative timestamp with the full date in title", async () => {
    render(<AuditLogTab />);
    const time = await screen.findByText("5 minutes ago");
    expect(time.tagName).toBe("TIME");
    expect(time.getAttribute("title")).toBeTruthy();
  });

  it("shows loading, error and empty states", async () => {
    vi.mocked(api.listAudit).mockRejectedValueOnce(new Error("x"));
    const { unmount } = render(<AuditLogTab />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /failed to load audit log/i,
    );
    unmount();
    vi.mocked(api.listAudit).mockResolvedValueOnce(page([]) as never);
    render(<AuditLogTab />);
    expect(await screen.findByText("No audit log entries")).toBeTruthy();
  });

  it("sends search and date filters and exports with the same filters", async () => {
    vi.mocked(api.exportAuditCsv).mockResolvedValue("time,actor\n");
    render(<AuditLogTab />);
    await screen.findByText("Invite created");
    await userEvent.type(screen.getByRole("searchbox"), "sso");
    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "2026-01-02" },
    });
    await waitFor(() => {
      const f = vi.mocked(api.listAudit).mock.calls.at(-1)?.[0];
      expect(f?.q).toBe("sso");
      expect(f?.since).toBe("2026-01-02");
    });
    await userEvent.click(screen.getByRole("button", { name: /Export CSV/ }));
    await waitFor(() => {
      const f = vi.mocked(api.exportAuditCsv).mock.calls[0][0];
      expect(f.q).toBe("sso");
      expect(f.since).toBe("2026-01-02");
    });
  });

  it("pages on demand", async () => {
    vi.mocked(api.listAudit).mockResolvedValue(page([entry], "c1") as never);
    render(<AuditLogTab />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Load more" }),
    );
    await waitFor(() =>
      expect(vi.mocked(api.listAudit).mock.calls.at(-1)?.[1]).toBe("c1"),
    );
  });
});

describe("auditQuery", () => {
  const none = { q: "", action: "", since: "", until: "" };
  it("drops empty filters and bounds the end date inclusively", () => {
    expect(api.auditQuery(none)).toBe("");
    expect(
      api.auditQuery({ ...none, q: " a b ", action: "oauth." }, "c", 50),
    ).toBe("?q=a+b&action_prefix=oauth.&cursor=c&limit=50");
    expect(api.auditQuery({ ...none, until: "2026-01-02" })).toMatch(
      /^\?until=2026-01-0[23]T/,
    );
  });
});
