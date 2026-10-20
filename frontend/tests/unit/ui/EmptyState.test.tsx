/**
 * @file tests/unit/ui/EmptyState.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { EmptyState } from "@/components/ui/EmptyState";

describe("EmptyState", () => {
  it("renders title, description, action", () => {
    render(
      <CssVarsProvider theme={joyTheme}>
        <EmptyState
          title="Quiet here"
          description="No posts yet."
          action={<button>Write one</button>}
        />
      </CssVarsProvider>,
    );
    expect(screen.getByText("Quiet here")).toBeInTheDocument();
    expect(screen.getByText("No posts yet.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /write one/i }),
    ).toBeInTheDocument();
  });
});
