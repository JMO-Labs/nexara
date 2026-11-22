/**
 * @file tests/unit/wishlists/draft.test.ts
 * @brief Wishlist wizard draft: step validation and API mapping.
 */
import { describe, it, expect } from "vitest";
import {
  draftError,
  initialDraft,
  toInput,
} from "@/components/wishlists/wizard/draft";
import { formatMoney, parseMoney } from "@/lib/money";

const me = { kind: "user" as const, ref_id: "u1", label: "Me" };

describe("wishlist draft", () => {
  it("validates per step", () => {
    const d = initialDraft(null, me);
    expect(draftError(d, 0)).toMatch(/title/);
    d.title = "Reunion";
    expect(draftError(d, 0)).toBeNull();
    expect(draftError({ ...d, recipients: [] }, 1)).toMatch(/who/);
    expect(
      draftError({ ...d, event_date: "2026-07-01", due_by: "2026-07-05" }, 2),
    ).toMatch(/buy-by/);
    expect(
      draftError({ ...d, budget_min_cents: 5000, budget_max_cents: 100 }, 2),
    ).toMatch(/minimum/);
    expect(
      draftError(
        { ...d, registry_links: [{ label: "x", url: "javascript:1" }] },
        2,
      ),
    ).toMatch(/http/);
  });

  it("maps to the API body", () => {
    const d = {
      ...initialDraft(null, me),
      title: " BBQ ",
      occasion: "party" as const,
      occasion_label: " ",
      recipients: [{ kind: "everyone" as const, label: "Everyone" }],
      registry_links: [
        { label: "", url: "https://www.amazon.com/registry/1" },
        { label: "Empty", url: " " },
      ],
    };
    const body = toInput(d);
    expect(body).toMatchObject({
      title: "BBQ",
      occasion_label: null,
      event_date: null,
      recipients: [{ kind: "everyone", ref_id: undefined, name: undefined }],
      registry_links: [
        { label: "Registry", url: "https://www.amazon.com/registry/1" },
      ],
    });
  });

  it("parses and formats money", () => {
    expect(parseMoney("$1,250.5")).toBe(125050);
    expect(parseMoney("")).toBeNull();
    expect(formatMoney(2500, "USD")).toMatch(/25/);
  });

  it("ships to a person or a typed address, never both", () => {
    const d = { ...initialDraft(null, me), title: "Bday" };
    expect(draftError({ ...d, ship_mode: "user" }, 2)).toMatch(/ship/);
    expect(draftError({ ...d, ship_mode: "text" }, 2)).toMatch(/address/);
    const byUser = toInput({
      ...d,
      ship_mode: "user",
      ship_to_user_id: "u9",
      ship_to_text: "x",
    });
    expect([byUser.ship_to_user_id, byUser.ship_to_text]).toEqual(["u9", null]);
    const none = toInput({ ...d, ship_mode: "none", ship_to_user_id: "u9" });
    expect([none.ship_to_user_id, none.ship_to_text]).toEqual([null, null]);
    expect(draftError({ ...d, ship_mode: "event" }, 2)).toMatch(/event/);
    const ev = toInput({ ...d, ship_mode: "event", ship_to_event_id: "e1" });
    expect([ev.ship_to_event_id, ev.ship_to_user_id]).toEqual(["e1", null]);
  });
});
