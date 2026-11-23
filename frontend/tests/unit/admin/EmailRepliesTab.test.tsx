/**
 * @file tests/unit/admin/EmailRepliesTab.test.tsx
 * @brief Email replies tab: setup steps, write-only password, API paths.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  apiPost: vi.fn(),
}));
vi.mock("@/lib/api/client", () => client);

import { EmailRepliesTab } from "@/components/admin/EmailRepliesTab";
import type { EmailReplySettings } from "@/lib/api/adminEmailReply";

const saved: EmailReplySettings = {
  imap_host: "imap.example.com",
  imap_port: 993,
  imap_user: "bot@example.com",
  reply_address: "reply@example.com",
  authserv_id: "mx.example.com",
  has_password: true,
  configured: true,
};

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <EmailRepliesTab />
    </QueryClientProvider>,
  );
}

describe("EmailRepliesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.apiGet.mockResolvedValue(saved);
    client.apiPut.mockResolvedValue(saved);
    client.apiPost.mockResolvedValue({ success: true, message: "Connected." });
  });

  it("loads from the /api/v1 path and shows setup steps", async () => {
    renderTab();
    expect(
      await screen.findByText(/settings are complete/),
    ).toBeInTheDocument();
    expect(client.apiGet).toHaveBeenCalledWith("/api/v1/admin/email-reply");
    expect(
      screen.getByText(/Create a mailbox just for replies/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Mailbox password")).toHaveAttribute(
      "placeholder",
      "Saved. Leave blank to keep it.",
    );
  });

  it("does not send a blank password", async () => {
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    await waitFor(() => expect(client.apiPut).toHaveBeenCalled());
    const [url, body] = client.apiPut.mock.calls[0];
    expect(url).toBe("/api/v1/admin/email-reply");
    expect(body).not.toHaveProperty("imap_password");
    expect(body.imap_port).toBe(993);
  });

  it("sends a typed password and runs the test", async () => {
    renderTab();
    fireEvent.change(await screen.findByLabelText("Mailbox password"), {
      target: { value: "app-pw" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(client.apiPut.mock.calls[0][1].imap_password).toBe("app-pw"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Test connection" }));
    expect(await screen.findByText("Connected.")).toBeInTheDocument();
    expect(client.apiPost).toHaveBeenCalledWith(
      "/api/v1/admin/email-reply/test",
    );
  });
});
