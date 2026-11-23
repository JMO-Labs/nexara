/**
 * @file tests/unit/settings/GravatarEmailInput.test.tsx
 * @brief Gravatar email saves on blur, shows server errors, can be disabled.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GravatarEmailInput } from "@/components/settings/GravatarEmailInput";
import * as hooks from "@/hooks/useSettings";
import * as api from "@/lib/api/settings";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/hooks/useSettings");
vi.mock("@/lib/api/settings");

const wrap = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>
    {children}
  </QueryClientProvider>
);

describe("GravatarEmailInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hooks.useUserSettings).mockReturnValue({
      data: { gravatar_email: null },
    } as any);
  });

  it("saves the trimmed value on blur", async () => {
    vi.mocked(api.updateProfile).mockResolvedValue({} as any);
    const user = userEvent.setup();
    render(<GravatarEmailInput loginEmail="me@x.io" />, { wrapper: wrap });
    const input = screen.getByLabelText("Gravatar email");
    expect(input).toHaveAttribute("placeholder", "me@x.io");
    await user.type(input, "pic@x.io ");
    await user.tab();
    await waitFor(() =>
      expect(api.updateProfile).toHaveBeenCalledWith({
        gravatar_email: "pic@x.io",
      }),
    );
  });

  it("does not save when unchanged", async () => {
    const user = userEvent.setup();
    render(<GravatarEmailInput />, { wrapper: wrap });
    await user.click(screen.getByLabelText("Gravatar email"));
    await user.tab();
    expect(api.updateProfile).not.toHaveBeenCalled();
  });

  it("shows an inline error on 422", async () => {
    vi.mocked(api.updateProfile).mockRejectedValue(
      new ApiError(422, "validation_error", "Invalid email"),
    );
    const user = userEvent.setup();
    render(<GravatarEmailInput />, { wrapper: wrap });
    await user.type(screen.getByLabelText("Gravatar email"), "nope");
    await user.tab();
    expect(await screen.findByText(/invalid email/i)).toBeInTheDocument();
  });

  it("is disabled when told", () => {
    render(<GravatarEmailInput disabled />, { wrapper: wrap });
    expect(screen.getByLabelText("Gravatar email")).toBeDisabled();
  });
});
