/**
 * @file tests/unit/lib/profile.test.ts
 * @brief Social detection, vCard export and birthday text.
 */
import { describe, it, expect } from "vitest";
import { birthdayText, mapsUrl, socialFor, toVCard } from "@/lib/profile";
import type { UserProfile } from "@/lib/api/users";

describe("socialFor", () => {
  it("detects brands by host and Mastodon by /@user", () => {
    expect(socialFor("https://www.instagram.com/ruth")?.title).toBe(
      "Instagram",
    );
    expect(socialFor("https://twitter.com/x")?.title).toBe("X");
    expect(socialFor("https://m.facebook.com/a")?.title).toBe("Facebook");
    expect(socialFor("https://mastodon.social/@ruth")?.title).toBe("Mastodon");
    expect(socialFor("https://example.com/blog")).toBeNull();
    expect(socialFor("not a url")).toBeNull();
    expect(socialFor("https://notinstagram.com/x")).toBeNull();
  });
});

describe("toVCard", () => {
  it("includes only shared fields and escapes", () => {
    const p = {
      display_name: "Ruth Alvarez",
      phone: "555-0100",
      contact_email: null,
      address: "1 Main St, Apt 2",
      birthday: "--11-24",
      links: [{ label: "", url: "https://instagram.com/ruth" }],
    } as unknown as UserProfile;
    const v = toVCard(p);
    expect(v).toContain("FN:Ruth Alvarez\r\n");
    expect(v).toContain("N:Alvarez;Ruth;;;");
    expect(v).toContain("TEL;TYPE=CELL:555-0100");
    expect(v).toContain("ADR;TYPE=HOME:;;1 Main St\\, Apt 2;;;;");
    expect(v).toContain("BDAY:--11-24");
    expect(v).not.toContain("EMAIL");
    expect(v.endsWith("END:VCARD\r\n")).toBe(true);
  });
});

describe("birthdayText / mapsUrl", () => {
  it("hides the year when the API does", () => {
    expect(birthdayText("--11-24")).not.toMatch(/\d{4}/);
    expect(birthdayText("1948-11-24")).toMatch(/1948/);
    expect(mapsUrl("1 Main St")).toContain("query=1%20Main%20St");
  });
});
