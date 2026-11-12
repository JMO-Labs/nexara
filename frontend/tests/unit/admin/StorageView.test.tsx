/**
 * @file tests/unit/admin/StorageView.test.tsx
 * @brief Storage analytics page: summary, charts, sortable user table.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/adminStorage";
import { StorageView } from "@/components/admin/StorageView";

vi.mock("@/lib/api/adminStorage", async (orig) => ({
  ...(await orig<typeof api>()),
  getStorage: vi.fn(),
  getStorageUsers: vi.fn(),
}));

const GB = 1024 ** 3;

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getStorage).mockResolvedValue({
    current: {
      total_bytes: 2 * GB,
      by_category: {
        images: GB,
        videos: GB / 2,
        thumbnails: 0,
        other: 0,
        db: GB / 2,
      },
    },
    snapshots: [
      { date: "2026-01-01", total_bytes: GB },
      { date: "2026-01-02", total_bytes: 2 * GB },
    ],
    per_user: [],
  });
  vi.mocked(api.getStorageUsers).mockResolvedValue({
    items: [
      {
        user_id: "a",
        display_name: "Zed",
        used_bytes: 100,
        percent_of_total: 10,
      },
      {
        user_id: "b",
        display_name: "Amy",
        used_bytes: 900,
        percent_of_total: 90,
      },
    ],
    total: 2,
    page: 1,
    page_size: 100,
  });
});

function renderView() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <StorageView />
    </QueryClientProvider>,
  );
}

describe("StorageView", () => {
  it("shows total, charts and categories", async () => {
    renderView();
    expect(await screen.findByText("2.0 GB")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /storage over time/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /category breakdown/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Images/)).toBeInTheDocument();
  });

  it("sorts users by name when header clicked", async () => {
    renderView();
    await screen.findByText("Zed");
    const rows = () =>
      screen
        .getAllByRole("row")
        .slice(1)
        .map((r) => r.textContent);
    expect(rows()[0]).toContain("Amy"); // default: bytes desc
    await userEvent.click(screen.getByRole("button", { name: /name/i }));
    expect(rows()[0]).toContain("Amy");
    await userEvent.click(screen.getByRole("button", { name: /name/i }));
    expect(rows()[0]).toContain("Zed");
  });
});
