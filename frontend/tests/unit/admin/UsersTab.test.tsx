/**
 * @file tests/unit/admin/UsersTab.test.tsx
 * @brief Tests for UsersTab component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as useAdminModule from "@/hooks/useAdmin";
import { UsersTab } from "@/components/admin/UsersTab";

vi.mock("@/hooks/useAdmin");

describe("UsersTab", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    vi.clearAllMocks();
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "Wrapper";
  const wrapper = Wrapper;

  it("should render loading state", () => {
    vi.mocked(useAdminModule.useAdminUsers).mockReturnValue({
      isLoading: true,
    } as any);

    render(<UsersTab />, { wrapper });

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("should render error state", () => {
    vi.mocked(useAdminModule.useAdminUsers).mockReturnValue({
      isLoading: false,
      error: new Error("Failed to load"),
    } as any);

    render(<UsersTab />, { wrapper });

    expect(screen.getByText(/failed to load users/i)).toBeInTheDocument();
  });

  it("should render users table with data", () => {
    const mockUsers = {
      items: [
        {
          id: "user-1",
          username: "john",
          display_name: "John Doe",
          email: "john@example.com",
          avatar_url: null,
          bio: null,
          title: null,
          location: null,
          website_url: null,
          role: "member",
          created_at: new Date(),
          last_seen_at: new Date(),
          status: "active",
        },
      ],
      next_cursor: null,
      has_more: false,
    };

    vi.mocked(useAdminModule.useAdminUsers).mockReturnValue({
      isLoading: false,
      data: mockUsers,
    } as any);

    const changeRoleMutation = {
      mutate: vi.fn(),
      isPending: false,
    };
    vi.mocked(useAdminModule.useChangeUserRole).mockReturnValue(
      changeRoleMutation as any,
    );
    vi.mocked(useAdminModule.useSuspendUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(useAdminModule.useRestoreUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(useAdminModule.useDeleteUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<UsersTab />, { wrapper });

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("should render role as chip", () => {
    const mockUsers = {
      items: [
        {
          id: "user-1",
          username: "john",
          display_name: "John Doe",
          email: "john@example.com",
          avatar_url: null,
          bio: null,
          title: null,
          location: null,
          website_url: null,
          role: "admin",
          created_at: new Date(),
          last_seen_at: new Date(),
          status: "active",
        },
      ],
      next_cursor: null,
      has_more: false,
    };

    vi.mocked(useAdminModule.useAdminUsers).mockReturnValue({
      isLoading: false,
      data: mockUsers,
    } as any);

    vi.mocked(useAdminModule.useSuspendUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(useAdminModule.useRestoreUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(useAdminModule.useDeleteUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<UsersTab />, { wrapper });

    expect(screen.getByText("Admin")).toBeInTheDocument();
  });
});
