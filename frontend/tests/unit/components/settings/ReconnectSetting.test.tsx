/**
 * @file tests/unit/components/settings/ReconnectSetting.test.tsx
 * @brief ReconnectSetting: toggle and days select emit prefs patches.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import en from "@/i18n/en-US.json";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string, v?: { days?: number }) =>
    ((en.settings.notif as Record<string, string>)[k] ?? k).replace(
      "{days}",
      String(v?.days ?? ""),
    ),
}));

import { ReconnectSetting } from "@/components/settings/ReconnectSetting";

describe("ReconnectSetting", () => {
  it("toggles and picks days", async () => {
    const onChange = vi.fn();
    render(<ReconnectSetting enabled days={30} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Remind me to reconnect"));
    expect(onChange).toHaveBeenCalledWith({ reconnect_nudges: false });
    await userEvent.selectOptions(
      screen.getByLabelText("After this many quiet days"),
      "60",
    );
    expect(onChange).toHaveBeenCalledWith({ reconnect_days: 60 });
    expect(screen.getAllByRole("option")).toHaveLength(4);
  });

  it("disables the select when off", () => {
    render(<ReconnectSetting enabled={false} days={14} onChange={vi.fn()} />);
    expect(screen.getByLabelText("After this many quiet days")).toBeDisabled();
  });
});
