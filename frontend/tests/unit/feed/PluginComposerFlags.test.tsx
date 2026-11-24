/**
 * @file tests/unit/feed/PluginComposerFlags.test.tsx
 * @brief Composer flags render from enabled plugins and report values.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const ui = vi.hoisted(() => ({ data: [] as unknown[] }));
vi.mock("@/hooks/usePluginUi", () => ({
  usePluginUi: () => ({ data: ui.data }),
}));

import { PluginComposerFlags } from "@/components/feed/PluginComposerFlags";

const plugin = {
  plugin_id: "sassy",
  name: "Sassybot",
  user_prefs: {},
  composer_flags: {
    roast: { type: "boolean", label: "Roast me", default: false },
  },
};

describe("PluginComposerFlags", () => {
  it("renders nothing without flags", () => {
    ui.data = [{ ...plugin, composer_flags: {} }];
    const { container } = render(
      <PluginComposerFlags value={{}} onChange={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("reports toggled flag keyed by plugin", async () => {
    ui.data = [plugin];
    const onChange = vi.fn();
    render(<PluginComposerFlags value={{}} onChange={onChange} />);
    await userEvent
      .setup()
      .click(screen.getByRole("switch", { name: "Roast me" }));
    expect(onChange).toHaveBeenCalledWith({ sassy: { roast: true } });
  });

  it("clearing a number flag removes its key", async () => {
    ui.data = [
      {
        ...plugin,
        composer_flags: { n: { type: "number", label: "Count" } },
      },
    ];
    const onChange = vi.fn();
    render(
      <PluginComposerFlags value={{ sassy: { n: 3 } }} onChange={onChange} />,
    );
    await userEvent.setup().clear(screen.getByLabelText("Count"));
    expect(onChange).toHaveBeenLastCalledWith({});
  });
});
