/**
 * @file tests/unit/components/admin/UsersTabPolish.test.tsx
 * @brief Density store, error retry and virtualization for UsersTab.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import * as useAdminModule from "@/hooks/useAdmin";
import { UsersTab } from "@/components/admin/UsersTab";
import { useUI } from "@/stores/ui";

vi.mock("@/hooks/useAdmin");

const mut = { mutate: vi.fn(), isPending: false } as any;
const mkUsers = (n: number) => ({
  items: Array.from({ length: n }, (_, i) => ({
    id: `u${i}`,
    username: `user${i}`,
    display_name: `User ${i}`,
    email: `u${i}@x.io`,
    role: "member",
    status: "active",
  })),
  next_cursor: null,
  has_more: false,
});

beforeEach(() => {
  vi.clearAllMocks();
  useUI.setState({ density: "comfortable" });
  vi.mocked(useAdminModule.useSuspendUser).mockReturnValue(mut);
  vi.mocked(useAdminModule.useRestoreUser).mockReturnValue(mut);
  vi.mocked(useAdminModule.useDeleteUser).mockReturnValue(mut);
});

describe("UsersTab polish", () => {
  it("retries on error", () => {
    const refetch = vi.fn();
    vi.mocked(useAdminModule.useAdminUsersInfinite).mockReturnValue({
      isLoading: false,
      error: new Error("x"),
      refetch,
    } as any);
    render(<UsersTab />);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it("reads density from the shared UI store", () => {
    useUI.setState({ density: "compact" });
    vi.mocked(useAdminModule.useAdminUsersInfinite).mockReturnValue({
      isLoading: false,
      data: mkUsers(1),
    } as any);
    render(<UsersTab />);
    expect(screen.getByText("User 0").className).toContain("text-xs");
  });

  it("density select changes the store immediately", () => {
    vi.mocked(useAdminModule.useAdminUsersInfinite).mockReturnValue({
      isLoading: false,
      data: mkUsers(1),
    } as any);
    render(<UsersTab />);
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: "Compact" }));
    expect(useUI.getState().density).toBe("compact");
  });

  it("requests the next page when more are available", () => {
    const fetchNextPage = vi.fn();
    vi.mocked(useAdminModule.useAdminUsersInfinite).mockReturnValue({
      isLoading: false,
      data: { ...mkUsers(3), has_more: true, next_cursor: "c" },
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
    } as any);
    render(<UsersTab />);
    fireEvent.click(screen.getByRole("button", { name: /load more/i }));
    expect(fetchNextPage).toHaveBeenCalled();
  });

  it("virtualizes large lists", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      width: 800,
      height: 600,
      top: 0,
      left: 0,
      right: 800,
      bottom: 600,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(600);
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(800);
    vi.mocked(useAdminModule.useAdminUsersInfinite).mockReturnValue({
      isLoading: false,
      data: mkUsers(1000),
    } as any);
    render(<UsersTab />);
    const rows = screen.getAllByRole("row").length;
    expect(rows).toBeGreaterThan(1);
    expect(rows).toBeLessThan(100);
  });
});
