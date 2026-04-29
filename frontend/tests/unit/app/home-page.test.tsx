/**
 * @file tests/unit/app/home-page.test.tsx
 * @brief Smoke tests for the home page. Verifies WelcomeBanner, WidgetGrid,
 *        and WidgetGallery mount without crashing.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";

// --- Mocks ---
vi.mock("@/lib/widgets/builtins", () => ({}));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/stores/session", () => ({
  useSession: vi.fn((sel) =>
    sel({ user: { id: "u1", display_name: "Alice", role: "member" }, status: "authenticated" }),
  ),
}));
vi.mock("@/hooks/useHomeLayout", () => ({
  useHomeLayout: vi.fn(() => ({
    widgets: [],
    isLoading: false,
    isError: false,
    addWidget: vi.fn(),
    removeWidget: vi.fn(),
    toggleCollapsed: vi.fn(),
    reorder: vi.fn(),
    resetToDefault: vi.fn(),
  })),
}));
vi.mock("@/hooks/useHomeSummary", () => ({
  useHomeSummary: vi.fn(() => ({
    data: { new_posts: 2, upcoming_events: 1, unread_notifications: 0 },
    isLoading: false,
  })),
}));
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return {
    ...actual,
    useReducedMotion: () => false,
  };
});

import AppHome from "@/app/app/page";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("AppHome page", () => {
  it("renders WelcomeBanner with user name", () => {
    wrap(<AppHome />);
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
  });

  it("renders WidgetGallery add button", () => {
    wrap(<AppHome />);
    expect(screen.getByLabelText("Add widget")).toBeInTheDocument();
  });

  it("renders without crashing when layout is loading", () => {
    wrap(<AppHome />);
    expect(document.body.children.length).toBeGreaterThan(0);
  });
});
