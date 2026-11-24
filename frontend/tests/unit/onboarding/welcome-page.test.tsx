/**
 * @file tests/unit/onboarding/welcome-page.test.tsx
 * @brief /app/welcome sends finished members home unless ?resume=1.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const replace = vi.fn();
const params = vi.hoisted(() => ({ q: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(params.q),
}));
vi.mock("@/hooks/useOnboarding", () => ({
  useOnboarding: () => ({ data: { done: true, step: 6 } }),
}));
vi.mock("@/components/onboarding/WelcomeWizard", () => ({
  WelcomeWizard: () => <p>wizard</p>,
}));

import WelcomePage from "@/app/app/welcome/page";

beforeEach(() => vi.clearAllMocks());

describe("WelcomePage", () => {
  it("sends a finished member home", () => {
    params.q = "";
    render(<WelcomePage />);
    expect(replace).toHaveBeenCalledWith("/app");
    expect(screen.queryByText("wizard")).toBeNull();
  });
  it("opens the wizard for a finished member with resume=1", () => {
    params.q = "resume=1";
    render(<WelcomePage />);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText("wizard")).toBeInTheDocument();
  });
});
