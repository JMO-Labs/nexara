/**
 * @file tests/unit/ui/Skeleton.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { Skeleton } from "@/components/ui/Skeleton";

describe("Skeleton", () => {
  it("exposes status role and aria-busy", () => {
    render(
      <CssVarsProvider theme={joyTheme}>
        <Skeleton width={120} height={16} />
      </CssVarsProvider>,
    );
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-busy", "true");
  });
});
