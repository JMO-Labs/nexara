import { cn } from "@/lib/utils";
test("cn merges and dedupes tailwind classes", () => {
  expect(cn("px-2", "px-4", false && "hidden", "text-ink")).toBe(
    "px-4 text-ink",
  );
});
