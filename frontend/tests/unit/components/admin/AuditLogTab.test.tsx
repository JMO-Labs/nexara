/**
 * @file tests/unit/components/admin/AuditLogTab.test.tsx
 * @brief Audit log: sentence-case action labels, relative time, search filters.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import * as admin from "@/hooks/useAdmin";
import { AuditLogTab } from "@/components/admin/AuditLogTab";

vi.mock("@/hooks/useAdmin");

const entry = {
  id: "a1",
  action: "invite.created",
  actor_display_name: "Rosa",
  target_type: "invite",
  target_display: null,
  created_at: new Date(Date.now() - 5 * 60_000).toISOString(),
};

beforeEach(() => {
  vi.mocked(admin.useAuditLog).mockReturnValue({
    isLoading: false,
    error: null,
    data: { items: [entry], has_more: false, next_cursor: null },
  } as never);
});

describe("AuditLogTab", () => {
  it("shows the action as a sentence-case label", () => {
    render(<AuditLogTab />);
    expect(screen.getByText("Invite created")).toBeInTheDocument();
    expect(screen.queryByText("invite.created")).toBeNull();
  });

  it("shows a relative timestamp with the full date in title", () => {
    render(<AuditLogTab />);
    const time = screen.getByText("5 minutes ago");
    expect(time.tagName).toBe("TIME");
    expect(time.getAttribute("title")).toBeTruthy();
  });

  it("filters by action through a search field", () => {
    render(<AuditLogTab />);
    fireEvent.change(
      screen.getByRole("searchbox", { name: "Filter by action" }),
      { target: { value: "nomatch" } },
    );
    expect(screen.getByText("No entries match filters")).toBeInTheDocument();
  });
});
