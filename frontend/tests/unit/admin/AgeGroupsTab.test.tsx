/**
 * @file tests/unit/admin/AgeGroupsTab.test.tsx
 * @brief Age groups tab: approve removes the row; setting switch saves.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  apiPost: vi.fn(),
  seg: (s: string) => s,
}));
vi.mock("@/lib/api/client", () => client);

import { AgeGroupsTab } from "@/components/admin/AgeGroupsTab";

const B = "/api/v1/admin/age-groups";
const row = {
  id: "s1",
  subject_id: "u1",
  suggested_by: "u2",
  age_group: "teen",
  note: "Turned 14",
  status: "pending",
  created_at: "2026-01-01T00:00:00Z",
};

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <AgeGroupsTab />
    </QueryClientProvider>,
  );
}

describe("AgeGroupsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.apiGet.mockImplementation(async (u: string) =>
      u.startsWith(`${B}/suggestions`)
        ? [row]
        : { adult_requires_approval: false },
    );
  });

  it("approve posts and removes the row", async () => {
    client.apiPost.mockResolvedValue({ ...row, status: "approved" });
    renderTab();
    expect(await screen.findByText("Turned 14")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /approve teen/i }));
    await waitFor(() =>
      expect(client.apiPost).toHaveBeenCalledWith(
        `${B}/suggestions/s1/approve`,
      ),
    );
    await waitFor(() =>
      expect(screen.queryByText("Turned 14")).not.toBeInTheDocument(),
    );
  });

  it("reject posts to reject endpoint", async () => {
    client.apiPost.mockResolvedValue(row);
    renderTab();
    fireEvent.click(
      await screen.findByRole("button", { name: /reject teen/i }),
    );
    await waitFor(() =>
      expect(client.apiPost).toHaveBeenCalledWith(`${B}/suggestions/s1/reject`),
    );
  });

  it("switch saves the setting", async () => {
    client.apiPut.mockResolvedValue({ adult_requires_approval: true });
    renderTab();
    fireEvent.click(await screen.findByRole("switch"));
    await waitFor(() =>
      expect(client.apiPut).toHaveBeenCalledWith(`${B}/settings`, {
        adult_requires_approval: true,
      }),
    );
  });
});
