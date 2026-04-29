/**
 * @file tests/unit/components/home/WidgetGallery.test.tsx
 * @brief Unit tests for WidgetGallery component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { clearRegistry, register } from "@/lib/widgets/registry";
import { WidgetGallery } from "@/components/home/WidgetGallery";
import type { WidgetContext } from "@/lib/widgets/registry";

function DummyWidget(_: WidgetContext) {
  return <div>dummy</div>;
}

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("WidgetGallery", () => {
  beforeEach(() => {
    clearRegistry();
    register({
      id: "test-widget",
      title: "Test Widget",
      description: "A test widget",
      defaultSize: "sm",
      category: "core",
      Component: DummyWidget,
    });
  });

  afterEach(() => {
    clearRegistry();
  });

  it("renders the add widget button", () => {
    wrap(
      <WidgetGallery
        presentDefIds={[]}
        onAdd={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Add widget")).toBeInTheDocument();
  });

  it("opens drawer on button click", () => {
    wrap(
      <WidgetGallery
        presentDefIds={[]}
        onAdd={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("Add widget"));
    expect(screen.getByText("Test Widget")).toBeInTheDocument();
  });

  it("calls onAdd with defId when Add button clicked", () => {
    const onAdd = vi.fn();
    wrap(
      <WidgetGallery
        presentDefIds={[]}
        onAdd={onAdd}
        onReset={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("Add widget"));
    fireEvent.click(screen.getByLabelText("Add Test Widget widget"));
    expect(onAdd).toHaveBeenCalledWith("test-widget");
  });

  it("does not show widgets already in layout", () => {
    wrap(
      <WidgetGallery
        presentDefIds={["test-widget"]}
        onAdd={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("Add widget"));
    expect(screen.getByText("All widgets are already on your page.")).toBeInTheDocument();
  });
});
