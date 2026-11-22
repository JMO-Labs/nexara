/**
 * @file tests/unit/admin/ShoppingTab.test.tsx
 * @brief Shopping tab: status, setup steps, secret kept when left blank.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/adminShop";
import { ShoppingTab } from "@/components/admin/ShoppingTab";

vi.mock("@/lib/api/adminShop");

const saved: api.AmazonSettings = {
  client_id: "cid",
  partner_tag: "fam-20",
  marketplace: "www.amazon.com",
  has_secret: true,
  source: "admin",
};

function renderTab() {
  vi.mocked(api.getAmazon).mockResolvedValue(saved);
  vi.mocked(api.putAmazon).mockResolvedValue(saved);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ShoppingTab />
    </QueryClientProvider>,
  );
}

describe("ShoppingTab", () => {
  it("shows status and setup steps", async () => {
    renderTab();
    expect(
      await screen.findByText(/using the keys saved here/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Join Amazon Associates/)).toBeInTheDocument();
    expect(screen.getByLabelText("Client secret")).toHaveAttribute(
      "placeholder",
      "Saved. Leave blank to keep it.",
    );
  });

  it("does not send a blank secret", async () => {
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.putAmazon).toHaveBeenCalled());
    expect(vi.mocked(api.putAmazon).mock.calls[0][0]).not.toHaveProperty(
      "client_secret",
    );
  });
});
