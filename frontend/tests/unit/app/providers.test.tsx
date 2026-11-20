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

const loadPlugins = vi.fn(async () => {});
vi.mock("@/lib/plugins/plugin-loader", () => ({
  loadPlugins: () => loadPlugins(),
}));

import { act } from "@testing-library/react";
import Providers from "@/app/providers";
import { useSession } from "@/stores/session";

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

  it("loads plugins only once the session is authenticated", () => {
    // The manifest endpoint needs auth; fetching at boot 401'd on every page.
    loadPlugins.mockClear();
    useSession.setState({ status: "loading" });
    render(
      <Providers>
        <p>x</p>
      </Providers>,
    );
    expect(loadPlugins).not.toHaveBeenCalled();
    act(() => useSession.setState({ status: "authenticated" }));
    expect(loadPlugins).toHaveBeenCalledTimes(1);
  });
});
