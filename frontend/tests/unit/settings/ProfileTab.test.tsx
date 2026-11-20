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

const PROFILE = {
  display_name: "Ada L",
  bio: "Hello there",
  location: "London",
  website_url: "https://ada.example",
  title: "Engineer",
  pronouns: "she/her",
};

describe("ProfileTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    vi.mocked(settingsHooks.useMyProfile).mockReturnValue({
      data: PROFILE,
    } as any);
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
    await user.clear(input);
    await user.type(input, "they/them");
    expect(screen.getByText(/9\/50/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save profile/i }));
    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ pronouns: "they/them" }),
      );
    });
  });

  it("prefills fields from the current profile", () => {
    render(<ProfileTab />, { wrapper: createWrapper() });
    expect(screen.getByLabelText(/display name/i)).toHaveValue("Ada L");
    expect(screen.getByLabelText(/bio/i)).toHaveValue("Hello there");
    expect(screen.getByLabelText(/location/i)).toHaveValue("London");
    expect(screen.getByLabelText(/website/i)).toHaveValue(
      "https://ada.example",
    );
    expect(screen.getByLabelText(/title/i)).toHaveValue("Engineer");
  });

  it("fills fields when the profile arrives after first render", () => {
    vi.mocked(settingsHooks.useMyProfile).mockReturnValue({
      data: undefined,
    } as any);
    const { rerender } = render(<ProfileTab />, { wrapper: createWrapper() });
    expect(screen.getByLabelText(/display name/i)).toHaveValue("");
    vi.mocked(settingsHooks.useMyProfile).mockReturnValue({
      data: PROFILE,
    } as any);
    rerender(<ProfileTab />);
    expect(screen.getByLabelText(/display name/i)).toHaveValue("Ada L");
  });

  it("sends only the changed display name", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateProfile).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as any);
    render(<ProfileTab />, { wrapper: createWrapper() });
    const input = screen.getByLabelText(/display name/i);
    await user.clear(input);
    await user.type(input, "Ada Lovelace");
    await user.click(screen.getByRole("button", { name: /save profile/i }));
    await waitFor(() =>
      expect(mockMutate).toHaveBeenCalledWith({ display_name: "Ada Lovelace" }),
    );
  });

  it("sends bio as empty string when cleared", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateProfile).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as any);
    render(<ProfileTab />, { wrapper: createWrapper() });
    await user.clear(screen.getByLabelText(/bio/i));
    await user.click(screen.getByRole("button", { name: /save profile/i }));
    await waitFor(() => expect(mockMutate).toHaveBeenCalledWith({ bio: "" }));
  });
});
