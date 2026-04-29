/**
 * @file tests/unit/components/home/WidgetFrame.test.tsx
 * @brief Unit tests for the WidgetFrame component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { useConfirmDialog } from "@/stores/confirmDialog";

vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    motion: {
      ...actual.motion,
      div: ({
        children,
        ...rest
      }: React.HTMLAttributes<HTMLDivElement> & {
        children?: React.ReactNode;
      }) => <div {...rest}>{children}</div>,
    },
  };
});

import { WidgetFrame } from "@/components/home/WidgetFrame";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("WidgetFrame", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Reset confirm dialog store
    useConfirmDialog.setState({
      isOpen: false,
      title: '',
      message: '',
      confirmLabel: 'Confirm',
      cancelLabel: 'Cancel',
      tone: 'neutral',
      _resolve: null,
    });
  });

  it("renders the widget title", () => {
    wrap(
      <WidgetFrame title="My Widget">
        <p>Content</p>
      </WidgetFrame>,
    );
    expect(
      screen.getByRole("heading", { name: /my widget/i }),
    ).toBeInTheDocument();
  });

  it("renders children content", () => {
    wrap(
      <WidgetFrame title="Widget">
        <p>Widget body</p>
      </WidgetFrame>,
    );
    expect(screen.getByText("Widget body")).toBeInTheDocument();
  });

  it("renders collapse toggle button with aria-expanded", () => {
    wrap(
      <WidgetFrame title="Widget" collapsed={false}>
        <p>Content</p>
      </WidgetFrame>,
    );
    const toggleBtn = screen.getByRole("button", { name: /collapse|expand/i });
    expect(toggleBtn).toHaveAttribute("aria-expanded", "true");
  });

  it("calls onToggleCollapsed when collapse button is clicked", async () => {
    const onToggle = vi.fn();
    wrap(
      <WidgetFrame
        title="Widget"
        collapsed={false}
        onToggleCollapsed={onToggle}
      >
        <p>Content</p>
      </WidgetFrame>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: /collapse|expand/i }),
    );
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("shows remove button and calls onRemove after confirm", async () => {
    const onRemove = vi.fn();
    // Mock confirm store to auto-accept
    const mockConfirm = vi.fn().mockResolvedValue(true);
    useConfirmDialog.setState({ confirm: mockConfirm } as any);
    wrap(
      <WidgetFrame title="Widget" onRemove={onRemove}>
        <p>Content</p>
      </WidgetFrame>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: /remove widget/i }),
    );
    expect(mockConfirm).toHaveBeenCalledOnce();
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("does not call onRemove when confirm is cancelled", async () => {
    const onRemove = vi.fn();
    const mockConfirm = vi.fn().mockResolvedValue(false);
    useConfirmDialog.setState({ confirm: mockConfirm } as any);
    wrap(
      <WidgetFrame title="Widget" onRemove={onRemove}>
        <p>Content</p>
      </WidgetFrame>,
    );
    await userEvent.click(
      screen.getByRole("button", { name: /remove widget/i }),
    );
    expect(onRemove).not.toHaveBeenCalled();
  });

  it("renders dragHandleSlot when provided", () => {
    wrap(
      <WidgetFrame
        title="Widget"
        dragHandleSlot={<span data-testid="drag-handle">drag</span>}
      >
        <p>Content</p>
      </WidgetFrame>,
    );
    expect(screen.getByTestId("drag-handle")).toBeInTheDocument();
  });

  it("does not render remove button when onRemove is not provided", () => {
    wrap(
      <WidgetFrame title="Widget">
        <p>Content</p>
      </WidgetFrame>,
    );
    expect(
      screen.queryByRole("button", { name: /remove widget/i }),
    ).not.toBeInTheDocument();
  });

  it("renders S/M/L/F size buttons when onSizeChange and currentSize provided", () => {
    wrap(
      <WidgetFrame
        title="Widget"
        currentSize="md"
        onSizeChange={vi.fn()}
      >
        <p>Content</p>
      </WidgetFrame>,
    );
    expect(screen.getByRole("button", { name: /resize widget to small/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /resize widget to medium/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /resize widget to large/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /resize widget to full/i })).toBeInTheDocument();
  });

  it("clicking size button calls onSizeChange with that size", async () => {
    const onSizeChange = vi.fn();
    wrap(
      <WidgetFrame
        title="Widget"
        currentSize="md"
        onSizeChange={onSizeChange}
      >
        <p>Content</p>
      </WidgetFrame>,
    );
    await userEvent.click(screen.getByRole("button", { name: /resize widget to large/i }));
    expect(onSizeChange).toHaveBeenCalledWith("lg");
  });

  it("header row has no nested buttons (collapse + remove are siblings, not children of another button)", () => {
    const onRemove = vi.fn();
    wrap(
      <WidgetFrame title="Widget" onRemove={onRemove}>
        <p>Content</p>
      </WidgetFrame>,
    );
    const buttons = screen.getAllByRole("button");
    // Each button must NOT contain another button
    for (const btn of buttons) {
      expect(btn.querySelectorAll("button")).toHaveLength(0);
    }
    // We expect exactly 2 buttons: collapse toggle + remove
    expect(buttons).toHaveLength(2);
  });
});
