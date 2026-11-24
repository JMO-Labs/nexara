/**
 * @file tests/unit/onboarding/steps.test.tsx
 * @brief Wizard steps: birthday saves only a complete plausible date on blur,
 *        profile pronouns, notify digest cadence.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const mutate = vi.fn();
vi.mock("@/hooks/useSettings", () => ({
  useMyProfile: () => ({
    data: { display_name: "Sam", avatar_url: null, birthday: null },
  }),
  useUpdateProfile: () => ({ mutate }),
}));
vi.mock("@/components/settings/AvatarPicker", () => ({
  AvatarPicker: () => <div />,
}));
vi.mock("@/components/settings/PushDevices", () => ({
  PushDevices: () => <p>push</p>,
}));
vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => k,
}));
const notif = vi.hoisted(() => ({
  getPreferences: vi.fn().mockResolvedValue({ recap_cadence: "weekly" }),
  patchPreferences: vi.fn().mockResolvedValue({}),
}));
vi.mock("@/lib/api/notifications", () => notif);

import { BirthdayStep } from "@/components/onboarding/steps/BirthdayStep";
import { ProfileStep } from "@/components/onboarding/steps/ProfileStep";
import { NotifyStep } from "@/components/onboarding/steps/NotifyStep";

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );

beforeEach(() => vi.clearAllMocks());

describe("BirthdayStep", () => {
  it("does not save while typing, saves a complete date on blur", () => {
    wrap(<BirthdayStep />);
    const input = screen.getByLabelText("Birthday");
    fireEvent.change(input, { target: { value: "0002-05-01" } });
    fireEvent.change(input, { target: { value: "1990-05-01" } });
    expect(mutate).not.toHaveBeenCalled();
    fireEvent.blur(input);
    expect(mutate).toHaveBeenCalledWith({ birthday: "1990-05-01" });
  });
  it("rejects an implausible year on blur", () => {
    wrap(<BirthdayStep />);
    const input = screen.getByLabelText("Birthday");
    fireEvent.change(input, { target: { value: "0020-05-01" } });
    fireEvent.blur(input);
    expect(mutate).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/1900/);
  });
});

describe("ProfileStep", () => {
  it("saves pronouns on blur", () => {
    wrap(
      <ProfileStep
        prefill={{ display_name: "Sam", avatar_url: null, email: "s@x.io" }}
      />,
    );
    const input = screen.getByLabelText("Pronouns");
    fireEvent.change(input, { target: { value: "they/them" } });
    fireEvent.blur(input);
    expect(mutate).toHaveBeenCalledWith({ pronouns: "they/them" });
  });
});

describe("NotifyStep", () => {
  it("offers push and the email digest cadence", async () => {
    wrap(<NotifyStep />);
    expect(screen.getByText("push")).toBeInTheDocument();
    const monthly = await screen.findByRole("radio", {
      name: "recap_monthly",
    });
    fireEvent.click(monthly);
    await waitFor(() =>
      expect(notif.patchPreferences).toHaveBeenCalledWith({
        recap_cadence: "monthly",
      }),
    );
  });
});
