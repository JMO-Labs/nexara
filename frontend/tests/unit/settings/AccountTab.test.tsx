/**
 * @file tests/unit/settings/AccountTab.test.tsx
 * @brief AccountTab component tests. Verify email form submission.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AccountTab } from "@/components/settings/AccountTab";
import * as settingsHooks from "@/hooks/useSettings";
import { useToasts } from "@/stores/toasts";

vi.mock("@/hooks/useSettings");

const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("AccountTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    vi.mocked(settingsHooks.useUpdateEmail).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
  });

  it("renders email form", () => {
    render(<AccountTab />, { wrapper: createWrapper() });

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
  });

  it("submits email form with new email", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateEmail).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);

    render(<AccountTab />, { wrapper: createWrapper() });

    const input = screen.getByLabelText(/email address/i) as HTMLInputElement;
    await user.clear(input);
    await user.type(input, "new@example.com");
    const button = screen.getByRole("button", { name: /update email/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith("new@example.com");
    });
  });

  it("shows loading state while submitting", async () => {
    vi.mocked(settingsHooks.useUpdateEmail).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: true,
      isSuccess: false,
    } as any);

    render(<AccountTab />, { wrapper: createWrapper() });

    const button = screen.getByRole("button", { name: /update email/i });
    expect(button).toBeDisabled();
  });
});
