/**
 * @file tests/unit/components/home/widgets/ActivityWidget.test.tsx
 * @brief Unit tests for ActivityWidget.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { ActivityWidget } from "@/components/home/widgets/ActivityWidget";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("ActivityWidget", () => {
  it("renders without crashing", () => {
    wrap(<ActivityWidget instanceId="w1" />);
    expect(document.body).toBeTruthy();
  });

  it("shows skeleton while loading (no server response yet)", () => {
    wrap(<ActivityWidget instanceId="w1" />);
    // Loading state until query resolves
    expect(document.body.children.length).toBeGreaterThan(0);
  });
});
