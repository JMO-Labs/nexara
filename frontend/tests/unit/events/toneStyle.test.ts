/**
 * @file tests/unit/events/toneStyle.test.ts
 * @brief Event tones come from groupColor; chips are soft fill + ink text.
 */
import { describe, it, expect } from "vitest";
import { groupColor } from "@/lib/groupColor";
import { toneForEvent } from "@/components/events/eventColors";
import { chipStyle } from "@/components/events/toneStyle";
import { makeEvent } from "./fixtures";

describe("toneForEvent", () => {
  it("community events use the community group colour", () => {
    expect(toneForEvent(makeEvent()).solid).toBe(groupColor(null));
  });

  it("subgroup events use groupColor of the subgroup id", () => {
    const ev = makeEvent({ visibility: "subgroup", subgroup_id: "sg-42" });
    expect(toneForEvent(ev).solid).toBe(groupColor("sg-42"));
  });

  it("an explicit event colour wins", () => {
    expect(toneForEvent(makeEvent({ color: "#112233" })).solid).toBe("#112233");
  });
});

describe("chipStyle", () => {
  const tone = toneForEvent(makeEvent({ color: "#112233" }));

  it("uses a 22% group-colour fill and ink text, with no border rail", () => {
    const s = chipStyle(tone, false);
    expect(s.backgroundColor).toBe(
      "color-mix(in srgb, #112233 22%, transparent)",
    );
    expect(s.color).toBe("var(--nx-ink)");
    expect(s.borderColor).toBeUndefined();
  });

  it("emphasised chips get a stronger fill but keep ink text", () => {
    const s = chipStyle(tone, true);
    expect(s.backgroundColor).toBe(
      "color-mix(in srgb, #112233 40%, transparent)",
    );
    expect(s.color).toBe("var(--nx-ink)");
  });
});
