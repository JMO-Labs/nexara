/**
 * @file tests/unit/admin/EmailTab.test.tsx
 * @brief Email tab: presets, write-only password, API paths, test send.
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

import { EmailTab } from "@/components/admin/EmailTab";
import type { EmailSettings } from "@/lib/api/adminEmail";

const saved: EmailSettings = {
  host: "",
  port: 587,
  security: "starttls",
  user: "",
  from_addr: "",
  from_name: "",
  auth: "password",
  has_password: false,
  has_google_refresh: false,
  configured: false,
  last_ok_at: null,
  last_error: null,
};

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <EmailTab />
    </QueryClientProvider>,
  );
}

describe("EmailTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.apiGet.mockResolvedValue(saved);
    client.apiPut.mockResolvedValue(saved);
    client.apiPost.mockResolvedValue({ ok: true, error: null });
  });

  it("Gmail preset fills host, port and security and shows help", async () => {
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Gmail" }));
    expect(screen.getByLabelText("SMTP server")).toHaveValue("smtp.gmail.com");
    expect(screen.getByLabelText("Port")).toHaveValue(587);
    expect(screen.getByLabelText("Security")).toHaveValue("starttls");
    expect(
      screen.getByRole("link", { name: "Create an app password" }),
    ).toHaveAttribute("href", "https://myaccount.google.com/apppasswords");
    expect(screen.getByText(/2-Step Verification/)).toBeInTheDocument();
  });

  it("Outlook preset fills office365", async () => {
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Outlook" }));
    expect(screen.getByLabelText("SMTP server")).toHaveValue(
      "smtp.office365.com",
    );
  });

  it("does not send a blank password; sends a typed one", async () => {
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    await waitFor(() => expect(client.apiPut).toHaveBeenCalled());
    const [url, body] = client.apiPut.mock.calls[0];
    expect(url).toBe("/api/v1/admin/email");
    expect(body).not.toHaveProperty("password");
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "app-pw" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(client.apiPut.mock.calls[1][1].password).toBe("app-pw"),
    );
  });

  it("sends a test email and shows the error on failure", async () => {
    client.apiPost.mockResolvedValue({ ok: false, error: "535 bad login" });
    renderTab();
    fireEvent.change(await screen.findByLabelText("Send test to"), {
      target: { value: "a@b.co" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send test email" }));
    expect(await screen.findByText("535 bad login")).toBeInTheDocument();
    expect(client.apiPost).toHaveBeenCalledWith("/api/v1/admin/email/test", {
      to: "a@b.co",
    });
  });
});
