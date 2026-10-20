/**
 * @file tests/unit/components/home/WidgetGallery.test.tsx
 * @brief Unit tests for the controlled WidgetGallery drawer.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { clearRegistry, register } from "@/lib/widgets/registry";
import type { WidgetContext, WidgetInstance } from "@/lib/widgets/registry";

const mockAddWidget = vi.fn();
const mockResetToDefault = vi.fn();
let widgets: WidgetInstance[] = [];

vi.mock("@/hooks/useHomeLayout", () => ({
  useHomeLayout: () => ({
    widgets,
    isLoading: false,
    isError: false,
    addWidget: mockAddWidget,
    removeWidget: vi.fn(),
    toggleCollapsed: vi.fn(),
    reorder: vi.fn(),
    setSize: vi.fn(),
    resetToDefault: mockResetToDefault,
  }),
}));

import { WidgetGallery } from "@/components/home/WidgetGallery";

function DummyWidget(_: WidgetContext) {
  return <div>dummy</div>;
}

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("WidgetGallery", () => {
  beforeEach(() => {
    mockAddWidget.mockClear();
    mockResetToDefault.mockClear();
    widgets = [];
    clearRegistry();
    register({
      id: "test-widget",
      title: "Test Widget",
      description: "A test widget",
      defaultSize: 3,
      category: "core",
      Component: DummyWidget,
    });
  });

  afterEach(() => {
    clearRegistry();
  });

  it("lists available widgets when open", () => {
    wrap(<WidgetGallery open onClose={vi.fn()} />);
    expect(screen.getByText("Test Widget")).toBeInTheDocument();
  });

  it("calls addWidget with defId when Add clicked", () => {
    const onClose = vi.fn();
    wrap(<WidgetGallery open onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Add Test Widget widget"));
    expect(mockAddWidget).toHaveBeenCalledWith("test-widget");
    expect(onClose).toHaveBeenCalled();
  });

  it("hides widgets already in layout", () => {
    widgets = [
      {
        id: "w1",
        defId: "test-widget",
        x: 0,
        y: 0,
        w: 3,
        h: 4,
        collapsed: false,
      },
    ];
    wrap(<WidgetGallery open onClose={vi.fn()} />);
    expect(
      screen.getByText("All widgets are already on your dashboard."),
    ).toBeInTheDocument();
  });
});
