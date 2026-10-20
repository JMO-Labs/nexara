/**
 * @file tests/unit/ui/Toast.test.tsx
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { ToastRoot } from "@/components/ui/Toast";
import { useToasts } from "@/stores/toasts";

describe("ToastRoot", () => {
  beforeEach(() => useToasts.getState().clear());

  it("renders pushed toasts in a live region", () => {
    render(
      <CssVarsProvider theme={joyTheme}>
        <ToastRoot />
      </CssVarsProvider>,
    );
    act(() => {
      useToasts.getState().push({
        variant: "success",
        title: "Saved",
        message: "Profile updated",
        ttl: 999_999,
      });
    });
    expect(
      screen.getByRole("region", { name: /notifications/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.getByText("Profile updated")).toBeInTheDocument();
  });
});
