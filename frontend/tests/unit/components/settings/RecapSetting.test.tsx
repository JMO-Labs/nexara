/**
 * @file tests/unit/components/settings/RecapSetting.test.tsx
 * @brief RecapSetting: shows cadence; choosing Off reports "off".
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import en from "@/i18n/en-US.json";
import { RecapSetting } from "@/components/settings/RecapSetting";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) =>
    (en.settings.notif as Record<string, string>)[k] ?? k,
}));

describe("RecapSetting", () => {
  it("checks the current cadence", () => {
    render(<RecapSetting value="monthly" onChange={() => {}} />);
    expect(screen.getByRole("radio", { name: "Monthly" })).toBeChecked();
  });

  it("calls onChange with off", async () => {
    const onChange = vi.fn();
    render(<RecapSetting value="weekly" onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio", { name: "Off" }));
    expect(onChange).toHaveBeenCalledWith("off");
  });
});
