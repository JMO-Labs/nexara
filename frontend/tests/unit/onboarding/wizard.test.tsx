/**
 * @file tests/unit/onboarding/wizard.test.tsx
 * @brief Gate redirect, wizard step flow, resume, SSO prefill, required blocking.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/errors";
import type { OnboardingState } from "@/lib/api/onboarding";

const replace = vi.fn();
let path = "/app";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => path,
}));
const api = vi.hoisted(() => ({
  getOnboarding: vi.fn(),
  putOnboardingStep: vi.fn().mockResolvedValue({}),
  completeOnboarding: vi.fn(),
}));
vi.mock("@/lib/api/onboarding", () => api);
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ status: "authenticated" }),
}));
vi.mock("@/hooks/useSettings", () => ({
  useMyProfile: () => ({ data: { display_name: "Sso Sam", avatar_url: null } }),
  useUpdateProfile: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/components/settings/AvatarPicker", () => ({
  AvatarPicker: () => <div />,
}));
vi.mock("@/components/onboarding/steps/BirthdayStep", () => ({
  BirthdayStep: () => <p>birthday-editor</p>,
}));
vi.mock("@/components/onboarding/steps/ContactStep", () => ({
  ContactStep: () => <p>contact-editor</p>,
}));
vi.mock("@/components/onboarding/steps/FamilyStep", () => ({
  FamilyStep: () => <p>family-editor</p>,
}));
vi.mock("@/components/onboarding/steps/NotifyStep", () => ({
  NotifyStep: () => <p>notify-editor</p>,
}));
vi.mock("@/components/onboarding/steps/SecurityStep", () => ({
  SecurityStep: () => <p>security-editor</p>,
}));

import { useOnboardingGate } from "@/components/onboarding/OnboardingGate";
import { WelcomeWizard } from "@/components/onboarding/WelcomeWizard";

const STEPS = [
  "profile",
  "birthday",
  "contact",
  "family",
  "notify",
  "security",
];
const state = (o: Partial<OnboardingState> = {}): OnboardingState =>
  ({
    step: 0,
    done: false,
    required: [],
    steps: STEPS,
    prefill: { display_name: "Sso Sam", avatar_url: null, email: "s@x.io" },
    ...o,
  }) as OnboardingState;

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );

function Probe() {
  useOnboardingGate();
  return null;
}

beforeEach(() => {
  vi.clearAllMocks();
  path = "/app";
});

describe("gate", () => {
  it("sends a member who is not done to /app/welcome", async () => {
    api.getOnboarding.mockResolvedValue(state());
    wrap(<Probe />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app/welcome"));
  });
  it("leaves the wizard and finished members alone", async () => {
    path = "/app/welcome";
    api.getOnboarding.mockResolvedValue(state());
    wrap(<Probe />);
    await waitFor(() => expect(api.getOnboarding).toHaveBeenCalled());
    expect(replace).not.toHaveBeenCalled();
  });
  it("does not redirect when done", async () => {
    api.getOnboarding.mockResolvedValue(state({ done: true }));
    wrap(<Probe />);
    await waitFor(() => expect(api.getOnboarding).toHaveBeenCalled());
    expect(replace).not.toHaveBeenCalled();
  });
});

describe("wizard", () => {
  it("shows the SSO prefilled name and progress", () => {
    wrap(<WelcomeWizard state={state()} />);
    expect(screen.getByLabelText("Display name")).toHaveValue("Sso Sam");
    expect(screen.getByText("Step 1 of 6")).toBeInTheDocument();
  });

  it("skip advances, persists and moves focus to the heading", async () => {
    wrap(<WelcomeWizard state={state()} />);
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    expect(await screen.findByText("birthday-editor")).toBeInTheDocument();
    expect(api.putOnboardingStep).toHaveBeenCalledWith(1);
    expect(screen.getByText("Step 2 of 6")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1 })).toHaveFocus(),
    );
  });

  it("resumes at the saved step and goes back", async () => {
    wrap(<WelcomeWizard state={state({ step: 2 })} />);
    expect(screen.getByText("contact-editor")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByText("birthday-editor")).toBeInTheDocument();
  });

  it("hides Skip on a required step", () => {
    wrap(<WelcomeWizard state={state({ step: 1, required: ["birthday"] })} />);
    expect(screen.queryByRole("button", { name: "Skip for now" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Continue" }),
    ).toBeInTheDocument();
  });

  it("finish with a missing required step shows the error and jumps there", async () => {
    api.completeOnboarding.mockRejectedValue(
      new ApiError(
        400,
        "onboarding_incomplete",
        "Finish the required steps first",
        {
          missing: ["birthday"],
        },
      ),
    );
    wrap(<WelcomeWizard state={state({ step: 5, required: ["birthday"] })} />);
    fireEvent.click(screen.getByRole("button", { name: "Finish" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /required steps/,
    );
    expect(screen.getByText("birthday-editor")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("finish completes and goes home", async () => {
    api.completeOnboarding.mockResolvedValue(state({ done: true }));
    wrap(<WelcomeWizard state={state({ step: 5 })} />);
    fireEvent.click(screen.getByRole("button", { name: "Finish" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
  });
});
