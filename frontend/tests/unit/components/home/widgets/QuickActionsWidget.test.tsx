/**
 * @file tests/unit/components/home/widgets/QuickActionsWidget.test.tsx
 * @brief Unit tests for QuickActionsWidget.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";

const mockShow = vi.fn();
vi.mock("@/stores/modals", () => ({
  useModals: vi.fn((sel) => sel({ show: mockShow })),
}));

import { QuickActionsWidget } from "@/components/home/widgets/QuickActionsWidget";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("QuickActionsWidget", () => {
  it("renders three action buttons", () => {
    wrap(<QuickActionsWidget instanceId="w1" />);
    expect(screen.getByLabelText("New post")).toBeInTheDocument();
    expect(screen.getByLabelText("Create event")).toBeInTheDocument();
    expect(screen.getByLabelText("Upload media")).toBeInTheDocument();
  });

  it("calls show('create-post') on New post click", () => {
    wrap(<QuickActionsWidget instanceId="w1" />);
    fireEvent.click(screen.getByLabelText("New post"));
    expect(mockShow).toHaveBeenCalledWith("create-post");
  });

  it("calls show('create-event') on Create event click", () => {
    wrap(<QuickActionsWidget instanceId="w1" />);
    fireEvent.click(screen.getByLabelText("Create event"));
    expect(mockShow).toHaveBeenCalledWith("create-event");
  });

  it("calls show('create-gallery') on Upload media click", () => {
    wrap(<QuickActionsWidget instanceId="w1" />);
    fireEvent.click(screen.getByLabelText("Upload media"));
    expect(mockShow).toHaveBeenCalledWith("create-gallery");
  });
});
