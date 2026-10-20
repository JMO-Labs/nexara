/**
 * @file tests/unit/ui/Toast.test.tsx
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
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
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });
});
