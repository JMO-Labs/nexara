/**
 * @file tests/unit/settings/AvatarPicker.test.tsx
 * @brief Profile photo: upload emits the media id; remove only for uploads.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AvatarPicker } from "@/components/settings/AvatarPicker";

const mutateAsync = vi.fn().mockResolvedValue("m1");
vi.mock("@/hooks/useMediaUpload", () => ({
  useMediaUpload: () => ({ mutateAsync, isPending: false, progress: 0 }),
}));

describe("AvatarPicker", () => {
  it("uploads a chosen image and reports its id", async () => {
    const onChange = vi.fn();
    const { container } = render(
      <AvatarPicker name="Ruth" src={null} onChange={onChange} />,
    );
    expect(screen.queryByRole("button", { name: /Remove/ })).toBeNull();
    const file = new File(["x"], "me.png", { type: "image/png" });
    fireEvent.change(container.querySelector("input[type=file]")!, {
      target: { files: [file] },
    });
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("m1"));
  });

  it("offers remove for an uploaded photo but not for Gravatar", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <AvatarPicker
        name="R"
        src="/api/v1/media/m1/thumbnail"
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Remove/ }));
    expect(onChange).toHaveBeenCalledWith(null);
    rerender(
      <AvatarPicker
        name="R"
        src="https://www.gravatar.com/avatar/abc"
        onChange={onChange}
      />,
    );
    expect(screen.queryByRole("button", { name: /Remove/ })).toBeNull();
    expect(
      screen.getByRole("button", { name: /Upload photo/ }),
    ).toBeInTheDocument();
  });
});
