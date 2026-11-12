/**
 * @file tests/unit/settings/ProfileTab.test.tsx
 * @brief ProfileTab component tests. Verify profile form submission.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProfileTab } from "@/components/settings/ProfileTab";
import * as settingsHooks from "@/hooks/useSettings";
import { useToasts } from "@/stores/toasts";

vi.mock("@/hooks/useSettings");

const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("ProfileTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    vi.mocked(settingsHooks.useUpdateProfile).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
  });

  it("renders profile form fields", () => {
    render(<ProfileTab />, { wrapper: createWrapper() });

    expect(screen.getByLabelText(/display name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/bio/i)).toBeInTheDocument();
  });

  it("submits profile form with updated data", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateProfile).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);

    render(<ProfileTab />, { wrapper: createWrapper() });

    const displayNameInput = screen.getByLabelText(
      /display name/i,
    ) as HTMLInputElement;
    await user.clear(displayNameInput);
    await user.type(displayNameInput, "Jane Doe");

    const button = screen.getByRole("button", { name: /save profile/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ display_name: "Jane Doe" }),
      );
    });
  });

  it("disables button while saving", () => {
    vi.mocked(settingsHooks.useUpdateProfile).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: true,
      isSuccess: false,
    } as any);

    render(<ProfileTab />, { wrapper: createWrapper() });

    const button = screen.getByRole("button", { name: /save profile/i });
    expect(button).toBeDisabled();
  });

  it("saves pronouns and shows char count", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateProfile).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);

    render(<ProfileTab />, { wrapper: createWrapper() });

    const input = screen.getByLabelText(/pronouns \(optional\)/i);
    expect(input).toHaveAttribute("maxlength", "50");
    await user.type(input, "they/them");
    expect(screen.getByText(/9\/50/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save profile/i }));
    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ pronouns: "they/them" }),
      );
    });
  });
});
