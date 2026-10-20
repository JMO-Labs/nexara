/**
 * @file tests/unit/ui/IconButton.test.tsx
 * @brief Test IconButton with tooltip and shortcut props.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { IconButton } from "@/components/ui/IconButton";
import * as React from "react";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("IconButton", () => {
  it("renders without tooltip", () => {
    wrap(<IconButton aria-label="save">💾</IconButton>);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("shows tooltip on hover", async () => {
    wrap(
      <IconButton tooltip="Save" aria-label="save">
        💾
      </IconButton>,
    );
    fireEvent.mouseOver(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
    });
  });

  it("displays shortcut in tooltip", async () => {
    wrap(
      <IconButton tooltip="Save" shortcut="Ctrl+S" aria-label="save">
        💾
      </IconButton>,
    );
    fireEvent.mouseOver(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("Save")).toBeInTheDocument();
      expect(screen.getByText("Ctrl+S")).toBeInTheDocument();
    });
  });

  it("ignores shortcut prop when no tooltip", () => {
    wrap(
      <IconButton shortcut="Ctrl+S" aria-label="save">
        💾
      </IconButton>,
    );
    expect(screen.getByRole("button")).toBeInTheDocument();
  });
});
