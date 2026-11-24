/**
 * @file tests/unit/onboarding/CompleteProfileCard.test.tsx
 * @brief Home card shows for sparse profiles and dismisses via settings.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

const hooks = vi.hoisted(() => ({
  settings: { profile_card_dismissed: false } as Record<string, boolean>,
  me: { id: "u1", avatar_url: null, birthday: null } as Record<string, unknown>,
  rel: [] as unknown[],
  mutate: vi.fn(),
}));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: hooks.settings }),
  useMyProfile: () => ({ data: hooks.me }),
  useUpdateSettings: () => ({ mutate: hooks.mutate }),
}));
vi.mock("@/hooks/useRelations", () => ({
  useRelations: () => ({ data: hooks.rel }),
}));
vi.mock("@/hooks/useOnboarding", () => ({
  useOnboarding: () => ({ data: { done: true } }),
}));

import { CompleteProfileCard } from "@/components/home/CompleteProfileCard";

describe("CompleteProfileCard", () => {
  it("lists what is missing and dismisses", () => {
    render(<CompleteProfileCard />);
    expect(
      screen.getByText(/a profile photo, your birthday, your family/),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Dismiss profile reminder" }),
    );
    expect(hooks.mutate).toHaveBeenCalledWith({ profile_card_dismissed: true });
  });
  it("Finish setup reopens the wizard for finished members", () => {
    render(<CompleteProfileCard />);
    expect(screen.getByRole("link", { name: "Finish setup" })).toHaveAttribute(
      "href",
      "/app/welcome?resume=1",
    );
  });
  it("hides when dismissed or complete", () => {
    hooks.settings.profile_card_dismissed = true;
    const { container, rerender } = render(<CompleteProfileCard />);
    expect(container).toBeEmptyDOMElement();
    hooks.settings.profile_card_dismissed = false;
    hooks.me = { id: "u1", avatar_url: "a", birthday: "2000-01-01" };
    hooks.rel = [{}];
    rerender(<CompleteProfileCard />);
    expect(container).toBeEmptyDOMElement();
  });
});
