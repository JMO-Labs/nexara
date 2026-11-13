/**
 * @file tests/unit/components/settings/DnDScheduleEditor.test.tsx
 * @brief DnDScheduleEditor: weekly grid, windows add/remove, timezone.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import en from "@/i18n/en-US.json";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) =>
    (en.settings.notif as Record<string, string>)[k] ?? k,
}));

import { DnDScheduleEditor } from "@/components/settings/DnDScheduleEditor";

describe("DnDScheduleEditor", () => {
  it("renders seven day rows", () => {
    render(
      <DnDScheduleEditor schedule={null} timezone="UTC" onChange={vi.fn()} />,
    );
    expect(screen.getAllByRole("group")).toHaveLength(7);
  });

  it("adds a window to a day", async () => {
    const onChange = vi.fn();
    render(
      <DnDScheduleEditor schedule={null} timezone="UTC" onChange={onChange} />,
    );
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Add window Mon" }));
    expect(onChange).toHaveBeenCalledWith(
      { mon: [{ start: "22:00", end: "07:00" }] },
      "UTC",
    );
  });

  it("supports multiple windows and removing one", async () => {
    const onChange = vi.fn();
    const schedule = {
      mon: [
        { start: "12:00", end: "13:00" },
        { start: "22:00", end: "23:00" },
      ],
    };
    render(
      <DnDScheduleEditor
        schedule={schedule}
        timezone="UTC"
        onChange={onChange}
      />,
    );
    expect(screen.getAllByLabelText("Start Mon")).toHaveLength(2);
    await userEvent
      .setup()
      .click(screen.getAllByRole("button", { name: "Remove window Mon" })[0]);
    expect(onChange).toHaveBeenCalledWith(
      { mon: [{ start: "22:00", end: "23:00" }] },
      "UTC",
    );
  });

  it("edits a time input", () => {
    const onChange = vi.fn();
    render(
      <DnDScheduleEditor
        schedule={{ tue: [{ start: "22:00", end: "07:00" }] }}
        timezone="UTC"
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText("End Tue"), {
      target: { value: "08:30" },
    });
    expect(onChange).toHaveBeenCalledWith(
      { tue: [{ start: "22:00", end: "08:30" }] },
      "UTC",
    );
  });

  it("changes timezone", () => {
    const onChange = vi.fn();
    render(
      <DnDScheduleEditor schedule={null} timezone="UTC" onChange={onChange} />,
    );
    fireEvent.change(screen.getByLabelText("Timezone"), {
      target: { value: "Europe/Paris" },
    });
    expect(onChange).toHaveBeenCalledWith(null, "Europe/Paris");
  });
});
