/**
 * @file tests/unit/settings/ProfileDetailsPanel.test.tsx
 * @brief Contact & about: prefill, validation, payload shape.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const mutate = vi.fn();
vi.mock("@/hooks/useSettings", () => ({
  useMyProfile: () => ({
    data: {
      id: "me",
      email: "login@x.io",
      contact_email: null,
      links: [],
      skills: [],
    },
  }),
  useUpdateProfile: () => ({ mutate, isPending: false }),
}));
vi.mock("@/components/settings/VisibilitySelect", () => ({
  VisibilitySelect: () => null,
}));
vi.mock("@/components/media/CoverPicker", () => ({ CoverPicker: () => null }));

import { ProfileDetailsPanel } from "@/components/settings/ProfileDetailsPanel";

describe("ProfileDetailsPanel", () => {
  beforeEach(() => mutate.mockReset());

  it("prefills contact email from sign-in email and saves parsed values", () => {
    renderWithProviders(<ProfileDetailsPanel />);
    expect(screen.getByLabelText("Contact email")).toHaveValue("login@x.io");
    fireEvent.change(screen.getByLabelText("Can help with"), {
      target: { value: " plumbing, , rides " },
    });
    fireEvent.click(screen.getByRole("button", { name: /Add link/ }));
    fireEvent.change(screen.getByLabelText("Link 1 URL"), {
      target: { value: "https://instagram.com/me" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    const body = mutate.mock.calls[0][0];
    expect(body.skills).toEqual(["plumbing", "rides"]);
    expect(body.links).toEqual([
      { label: "", url: "https://instagram.com/me" },
    ]);
    expect(body.emergency_contact).toBeNull();
    expect(body.birthday).toBeNull();
  });

  it("blocks bad links and half-filled emergency contact", () => {
    renderWithProviders(<ProfileDetailsPanel />);
    fireEvent.click(screen.getByRole("button", { name: /Add link/ }));
    fireEvent.change(screen.getByLabelText("Link 1 URL"), {
      target: { value: "javascript:alert(1)" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/http/);
    fireEvent.change(screen.getByLabelText("Link 1 URL"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("Emergency contact name"), {
      target: { value: "Sam" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/name and a phone/);
    expect(mutate).not.toHaveBeenCalled();
  });
});
