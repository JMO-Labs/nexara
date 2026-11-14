/**
 * @file tests/unit/auth/auth-layout.test.tsx
 * @brief The auth layout wrapper must not cap the card below 400px.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("@/components/ui/Toast", () => ({ ToastRoot: () => null }));

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
});
