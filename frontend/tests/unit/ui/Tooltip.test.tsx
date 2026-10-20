/**
 * @file tests/unit/ui/Tooltip.test.tsx
 * @brief Test Tooltip primitive with shortcut badge and disabled states.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { Tooltip } from "@/components/ui/Tooltip";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("Tooltip", () => {
  it("renders trigger and shows title on hover", async () => {
    wrap(
      <Tooltip title="Save">
        <button>btn</button>
      </Tooltip>,
    );
    fireEvent.mouseOver(screen.getByText("btn"));
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
    });
  });

  it("shortcut renders as kbd", async () => {
    wrap(
      <Tooltip title="Search" shortcut="Ctrl+K">
        <button>s</button>
      </Tooltip>,
    );
    fireEvent.mouseOver(screen.getByText("s"));
    await waitFor(() => {
      expect(screen.getByText("Ctrl+K")).toBeInTheDocument();
    });
  });

  it("disabled bypasses tooltip", () => {
    wrap(
      <Tooltip title="X" disabled>
        <span>plain</span>
      </Tooltip>,
    );
    expect(screen.getByText("plain")).toBeInTheDocument();
  });
});
