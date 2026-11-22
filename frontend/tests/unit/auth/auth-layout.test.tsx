/**
 * @file tests/unit/auth/auth-layout.test.tsx
 * @brief The auth layout is a full-page surface for the split AuthCard.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("@/components/ui/Toast", () => ({ ToastRoot: () => null }));
vi.mock("@/components/layout/AppBackdrop", () => ({
  AppBackdrop: () => <div data-testid="backdrop" />,
}));

import AuthLayout from "@/app/(auth)/layout";

describe("AuthLayout", () => {
  it("fills the page with no width cap or backdrop", () => {
    const { getByText, queryByTestId } = render(
      <AuthLayout>
        <span>child</span>
      </AuthLayout>,
    );
    const wrapper = getByText("child").parentElement as HTMLElement;
    expect(wrapper.className).toContain("min-h-dvh");
    expect(wrapper.className).not.toMatch(/max-w-/);
    expect(getByText("child").closest("main")?.className).toContain(
      "min-h-dvh",
    );
    expect(queryByTestId("backdrop")).toBeNull();
  });
});
