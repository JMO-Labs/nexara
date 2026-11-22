/**
 * @file tests/unit/auth/auth-layout.test.tsx
 * @brief The auth layout fits the split card (1080px), renders the shared
 *        backdrop, top-aligns on phones and centres from md up.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("@/components/ui/Toast", () => ({ ToastRoot: () => null }));
vi.mock("@/components/layout/AppBackdrop", () => ({
  AppBackdrop: () => <div data-testid="backdrop" />,
}));

import AuthLayout from "@/app/(auth)/layout";

describe("AuthLayout", () => {
  it("wraps children in the split-card width", () => {
    const { getByText } = render(
      <AuthLayout>
        <span>child</span>
      </AuthLayout>,
    );
    const wrapper = getByText("child").parentElement as HTMLElement;
    expect(wrapper.className).toContain("max-w-[1080px]");
    expect(wrapper.className).not.toContain("max-w-sm");
  });

  it("renders the backdrop, top-aligned on phones, centred on desktop", () => {
    const { getByTestId, getByText } = render(
      <AuthLayout>
        <span>child</span>
      </AuthLayout>,
    );
    expect(getByTestId("backdrop")).toBeTruthy();
    const main = getByText("child").closest("main") as HTMLElement;
    expect(main.className).toContain("items-start");
    expect(main.className).toContain("md:items-center");
  });
});
