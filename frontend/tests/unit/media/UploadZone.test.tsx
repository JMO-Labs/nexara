/**
 * @file tests/unit/media/UploadZone.test.tsx
 * @brief Keyboard path: visible "Choose files" button opens the file input.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("@/lib/api/media", () => ({ uploadFile: vi.fn() }));
import { UploadZone } from "@/components/media/UploadZone";

describe("UploadZone", () => {
  it("Choose files button triggers the hidden input", () => {
    const { container } = render(<UploadZone />);
    const input = container.querySelector(
      "input[type=file]",
    ) as HTMLInputElement;
    const click = vi.spyOn(input, "click");
    fireEvent.click(screen.getByRole("button", { name: "Choose files" }));
    expect(click).toHaveBeenCalled();
  });
});
