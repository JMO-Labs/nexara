/**
 * @file tests/unit/lib/mentions.test.ts
 * @brief linkifyMentions / activeMention.
 */
import { describe, it, expect } from "vitest";
import { activeMention, linkifyMentions } from "@/lib/mentions";
import { matchMembers } from "@/hooks/useMembersList";

describe("linkifyMentions", () => {
  it("links @names but not emails, URLs or code", () => {
    expect(linkifyMentions("hi @ruth!")).toBe("hi [@ruth](/app/u/ruth)!");
    expect(linkifyMentions("@maya first")).toBe("[@maya](/app/u/maya) first");
    expect(linkifyMentions("mail a@b.io")).toBe("mail a@b.io");
    expect(linkifyMentions("see x.com/@leo")).toBe("see x.com/@leo");
    expect(linkifyMentions("`@code` and @leo")).toBe(
      "`@code` and [@leo](/app/u/leo)",
    );
    expect(linkifyMentions("```\n@x\n```")).toBe("```\n@x\n```");
  });
});

describe("activeMention", () => {
  it("finds the @query before the caret", () => {
    expect(activeMention("hey @ru", 7)).toEqual({ start: 4, query: "ru" });
    expect(activeMention("@", 1)).toEqual({ start: 0, query: "" });
    expect(activeMention("a@b", 3)).toBeNull();
    expect(activeMention("hey @ruth done", 14)).toBeNull();
  });
});

describe("matchMembers", () => {
  const people = [
    {
      id: "1",
      username: "ruth",
      display_name: "Ruth Alvarez",
      avatar_url: null,
    },
    {
      id: "3",
      username: "jordan",
      display_name: "Jordan Lee",
      avatar_url: null,
    },
    { id: "2", username: "leo", display_name: "Leo Soto", avatar_url: null },
  ];
  it("matches username or any name word", () => {
    expect(matchMembers(people, "al").map((p) => p.id)).toEqual(["1"]);
    expect(matchMembers(people, "le").map((p) => p.id)).toEqual(["2", "3"]);
    expect(matchMembers(people, "")).toHaveLength(3);
  });
});
