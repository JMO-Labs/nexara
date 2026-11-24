/**
 * @file tests/unit/admin/sso/ProviderRules.test.tsx
 * @brief Allowed-domain chips: normalised add, labelled remove.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  ProviderRules,
  type RulesValue,
} from "@/components/admin/sso/ProviderRules";

const RULES: RulesValue = {
  auto_create_users: true,
  default_role: "member",
  allowed_domains: ["smith.family"],
  required_group: "",
  sync_profile: true,
};

describe("ProviderRules", () => {
  it("adds a normalised domain on Enter", async () => {
    const onChange = vi.fn();
    render(<ProviderRules value={RULES} onChange={onChange} />);
    await userEvent.type(
      screen.getByLabelText("Add domain"),
      " @Club.ORG {Enter}",
    );
    expect(onChange).toHaveBeenLastCalledWith({
      ...RULES,
      allowed_domains: ["smith.family", "club.org"],
    });
  });

  it("removes a domain chip", async () => {
    const onChange = vi.fn();
    render(<ProviderRules value={RULES} onChange={onChange} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Remove smith.family" }),
    );
    expect(onChange).toHaveBeenCalledWith({ ...RULES, allowed_domains: [] });
  });

  it("changes the default role", async () => {
    const onChange = vi.fn();
    render(<ProviderRules value={RULES} onChange={onChange} />);
    await userEvent.selectOptions(
      screen.getByLabelText("Default role"),
      "viewer",
    );
    expect(onChange).toHaveBeenCalledWith({ ...RULES, default_role: "viewer" });
  });
});
