/**
 * @file tests/unit/app/providers.test.tsx
 * @brief Providers use class-based next-themes with system default.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const captured: Record<string, unknown> = {};
vi.mock("next-themes", () => ({
  ThemeProvider: (
    props: Record<string, unknown> & { children: React.ReactNode },
  ) => {
    const { children, ...rest } = props;
    Object.assign(captured, rest);
    return <>{children}</>;
  },
}));

import Providers from "@/app/providers";

describe("Providers", () => {
  it("renders children with class-based system theme", () => {
    render(
      <Providers>
        <p>hi</p>
      </Providers>,
    );
    expect(screen.getByText("hi")).toBeVisible();
    expect(captured.attribute).toBe("class");
    expect(captured.defaultTheme).toBe("system");
  });
});
