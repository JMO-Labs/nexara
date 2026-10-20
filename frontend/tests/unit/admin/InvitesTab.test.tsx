/**
 * @file tests/unit/admin/InvitesTab.test.tsx
 * @brief Tests for InvitesTab component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as useInvitesModule from "@/hooks/useInvites";
import { InvitesTab } from "@/components/admin/InvitesTab";
import type { InviteResponse } from "@/lib/api/invites";

vi.mock("@/hooks/useInvites");

describe("InvitesTab", () => {
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
    vi.mocked(useInvitesModule.useInvites).mockReturnValue({
      isLoading: true,
    } as any);

    render(<InvitesTab />, { wrapper });

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("should render error state", () => {
    vi.mocked(useInvitesModule.useInvites).mockReturnValue({
      isLoading: false,
      error: new Error("Failed to load"),
    } as any);

    render(<InvitesTab />, { wrapper });

    expect(screen.getByText(/failed to load invites/i)).toBeInTheDocument();
  });

  it("should render invite form and list", () => {
    const mockInvites: InviteResponse[] = [
      {
        id: "invite-1",
        email: "test@example.com",
        role: "member",
        created_at: new Date("2024-01-01"),
        expires_at: new Date("2024-01-08"),
        used_at: null,
        code: "abc123",
      },
    ];

    vi.mocked(useInvitesModule.useInvites).mockReturnValue({
      isLoading: false,
      data: mockInvites,
    } as any);

    vi.mocked(useInvitesModule.useCreateInvite).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(useInvitesModule.useRevokeInvite).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<InvitesTab />, { wrapper });

    expect(screen.getByPlaceholderText(/email address/i)).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("should call createInvite on form submit", async () => {
    const mockInvites: InviteResponse[] = [];

    vi.mocked(useInvitesModule.useInvites).mockReturnValue({
      isLoading: false,
      data: mockInvites,
    } as any);

    const createMutation = {
      mutate: vi.fn(),
      isPending: false,
    };
    vi.mocked(useInvitesModule.useCreateInvite).mockReturnValue(
      createMutation as any,
    );

    vi.mocked(useInvitesModule.useRevokeInvite).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<InvitesTab />, { wrapper });

    const emailInput = screen.getByPlaceholderText(/email address/i);
    fireEvent.change(emailInput, { target: { value: "newuser@example.com" } });

    const form = emailInput.closest("form");
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(createMutation.mutate).toHaveBeenCalledWith({
        email: "newuser@example.com",
        role: "member",
      });
    });
  });
});
