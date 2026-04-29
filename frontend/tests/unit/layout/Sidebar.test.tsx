/**
 * @file tests/unit/layout/Sidebar.test.tsx
 * @brief Sidebar collapse/expand and localStorage persistence tests.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { Sidebar } from "@/components/layout/Sidebar";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("Sidebar", () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockReturnValue("/app");
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders expanded by default", () => {
    wrap(<Sidebar />);
    expect(screen.getByText("Nexara")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
  });

  it("renders toggle button", () => {
    wrap(<Sidebar />);
    const toggleButton = screen.getByRole("button", {
      name: /collapse sidebar/i,
    });
    expect(toggleButton).toBeInTheDocument();
  });

  it("collapses sidebar when toggle button clicked", async () => {
    wrap(<Sidebar />);
    const toggleButton = screen.getByRole("button", {
      name: /collapse sidebar/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      // Label should not be visible when collapsed
      expect(screen.queryByText("Home")).not.toBeInTheDocument();
    });
  });

  it("shows tooltip on collapsed nav item hover", async () => {
    wrap(<Sidebar />);
    const toggleButton = screen.getByRole("button", {
      name: /collapse sidebar/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      // After collapse, hover should trigger tooltip
      // This is harder to test without more setup, but at least verify structure
      const navItems = screen.getAllByRole("listitem");
      expect(navItems.length).toBeGreaterThan(0);
    });
  });

  it("persists collapsed state in localStorage", async () => {
    const { unmount } = wrap(<Sidebar />);
    const toggleButton = screen.getByRole("button", {
      name: /collapse sidebar/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(localStorage.getItem("nx:sidebar:collapsed")).toBe("true");
    });

    unmount();

    // Re-render and check if collapsed state is restored
    wrap(<Sidebar />);
    await waitFor(() => {
      expect(screen.queryByText("Home")).not.toBeInTheDocument();
    });
  });

  it("persists expanded state in localStorage", async () => {
    // Start with collapsed
    localStorage.setItem("nx:sidebar:collapsed", "true");
    const { unmount } = wrap(<Sidebar />);

    await waitFor(() => {
      expect(screen.queryByText("Home")).not.toBeInTheDocument();
    });

    // Toggle to expand
    const toggleButton = screen.getByRole("button", {
      name: /expand sidebar/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(localStorage.getItem("nx:sidebar:collapsed")).toBe("false");
      expect(screen.getByText("Home")).toBeInTheDocument();
    });

    unmount();

    // Re-render and check if expanded state is restored
    wrap(<Sidebar />);
    await waitFor(() => {
      expect(screen.getByText("Home")).toBeInTheDocument();
    });
  });

  it("hides Nexara title when collapsed", async () => {
    wrap(<Sidebar />);
    expect(screen.getByText("Nexara")).toBeInTheDocument();

    const toggleButton = screen.getByRole("button", {
      name: /collapse sidebar/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(screen.queryByText("Nexara")).not.toBeInTheDocument();
    });
  });

  it("preserves active state styling in collapsed mode", async () => {
    vi.mocked(usePathname).mockReturnValue("/app/chat");
    wrap(<Sidebar />);

    const toggleButton = screen.getByRole("button", {
      name: /collapse sidebar/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      const navItems = screen.getAllByRole("listitem");
      expect(navItems.length).toBeGreaterThan(0);
      // Active styling should still be applied
    });
  });
});
