/**
 * @file tests/unit/auth/auth-layout.test.tsx
 * @brief The auth layout wrapper must not cap the card below 400px, and
 *        renders the shared backdrop with a stable top-aligned card.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("@/components/ui/Toast", () => ({ ToastRoot: () => null }));
vi.mock("@/components/layout/AppBackdrop", () => ({
  AppBackdrop: () => <div data-testid="backdrop" />,
}));

import AuthLayout from "@/app/(auth)/layout";

describe("AuthLayout", () => {
  it("wraps children in a 400px max-width container", () => {
    const { getByText } = render(
      <AuthLayout>
        <span>child</span>
      </AuthLayout>,
    );
    const wrapper = getByText("child").parentElement as HTMLElement;
    expect(wrapper.className).toContain("max-w-[400px]");
    expect(wrapper.className).not.toContain("max-w-sm");
  });

  it("renders the app backdrop and top-aligns the card", () => {
    const { getByTestId, getByText } = render(
      <AuthLayout>
        <span>child</span>
      </AuthLayout>,
    );
    expect(getByTestId("backdrop")).toBeTruthy();
    const main = getByText("child").closest("main") as HTMLElement;
    expect(main.className).toContain("items-start");
    expect(main.className).toContain("pt-[12vh]");
    expect(main.className).not.toContain("items-center");
  });
});
