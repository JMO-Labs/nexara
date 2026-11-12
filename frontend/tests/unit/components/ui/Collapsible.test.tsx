/**
 * @file tests/unit/components/ui/Collapsible.test.tsx
 * @brief Unit tests for the Collapsible primitive.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Collapsible } from "@/components/ui/Collapsible";

// framer-motion AnimatePresence: make it a passthrough in test env
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

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("Collapsible", () => {
  it("renders the header slot", () => {
    wrap(
      <Collapsible open={true} header={<span>My Header</span>}>
        <p>Content</p>
      </Collapsible>,
    );
    expect(screen.getByText("My Header")).toBeInTheDocument();
  });

  it("shows content when open=true", () => {
    wrap(
      <Collapsible open={true} header="Header">
        <p>Visible content</p>
      </Collapsible>,
    );
    expect(screen.getByText("Visible content")).toBeInTheDocument();
  });

  it("hides content when open=false", () => {
    wrap(
      <Collapsible open={false} header="Header">
        <p>Hidden content</p>
      </Collapsible>,
    );
    expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
  });

  it("calls onOpenChange(false) when clicking header while open", async () => {
    const onOpenChange = vi.fn();
    wrap(
      <Collapsible open={true} onOpenChange={onOpenChange} header="Toggle me">
        <p>Content</p>
      </Collapsible>,
    );
    await userEvent.click(screen.getByRole("button", { name: /toggle me/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("calls onOpenChange(true) when clicking header while closed", async () => {
    const onOpenChange = vi.fn();
    wrap(
      <Collapsible open={false} onOpenChange={onOpenChange} header="Toggle me">
        <p>Content</p>
      </Collapsible>,
    );
    await userEvent.click(screen.getByRole("button", { name: /toggle me/i }));
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });

  it("sets aria-expanded correctly on header button", () => {
    const { rerender } = wrap(
      <>
        <Collapsible open={true} header="Header">
          <p>Content</p>
        </Collapsible>
      </>,
    );
    expect(screen.getByRole("button", { name: /header/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );

    rerender(
      <>
        <Collapsible open={false} header="Header">
          <p>Content</p>
        </Collapsible>
      </>,
    );
    expect(screen.getByRole("button", { name: /header/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("has aria-controls linking to panel id", () => {
    wrap(
      <Collapsible open={true} header="Header">
        <p>Content</p>
      </Collapsible>,
    );
    const btn = screen.getByRole("button", { name: /header/i });
    const panelId = btn.getAttribute("aria-controls");
    expect(panelId).toBeTruthy();
    expect(document.getElementById(panelId!)).toBeInTheDocument();
  });
});
