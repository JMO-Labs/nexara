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
});
