/**
 * @file tests/unit/ui/Toast.test.tsx
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToastRoot } from "@/components/ui/Toast";
import { useToasts } from "@/stores/toasts";

describe("ToastRoot", () => {
  beforeEach(() => useToasts.getState().clear());

  it("renders pushed toasts in a status region and dismisses", async () => {
    render(<ToastRoot />);
    act(() => {
      useToasts.getState().push({
        variant: "success",
        title: "Saved",
        message: "Profile updated",
        ttl: 999_999,
      });
    });
    const region = screen.getByRole("status");
    expect(region).toHaveTextContent("Saved");
    expect(region).toHaveTextContent("Profile updated");
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    await waitFor(() =>
      expect(screen.queryByText("Saved")).not.toBeInTheDocument(),
    );
  });

  it("renders an action button that calls onClick", async () => {
    const onClick = vi.fn();
    render(<ToastRoot />);
    act(() => {
      useToasts.getState().push({
        variant: "info",
        message: "Deleted",
        ttl: 999_999,
        action: { label: "Undo", onClick },
      });
    });
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("uses assertive aria-live for danger, polite otherwise", () => {
    render(<ToastRoot />);
    act(() => {
      useToasts
        .getState()
        .push({ variant: "danger", message: "Boom", ttl: 999_999 });
      useToasts
        .getState()
        .push({ variant: "info", message: "Fyi", ttl: 999_999 });
    });
    expect(screen.getByText("Boom").closest("[aria-live]")).toHaveAttribute(
      "aria-live",
      "assertive",
    );
    expect(screen.getByText("Fyi").closest("[aria-live]")).toHaveAttribute(
      "aria-live",
      "polite",
    );
  });
});
