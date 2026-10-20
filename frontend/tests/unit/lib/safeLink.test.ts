import { expect, test } from "vitest";
import { safeInternalLink } from "@/lib/safeLink";

test.each<[unknown, string | null]>([
  ["/app/post/1?x=1#c", "/app/post/1?x=1#c"],
  ["javascript:alert(1)", null],
  ["https://evil.com", null],
  ["//evil.com", null],
  ["/\\evil.com", null],
  [42, null],
  ["/.//evil.com", null],
  ["/..//evil.com", null],
  ["/./\\evil.com", null],
  ["/\t/evil.com", null],
])("safeInternalLink(%s)", (input, expected) => {
  expect(safeInternalLink(input)).toBe(expected);
});
