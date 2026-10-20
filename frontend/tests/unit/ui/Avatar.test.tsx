/**
 * @file tests/unit/ui/Avatar.test.tsx
 * @brief Avatar fallback behavior.
 */
import { render, screen } from "@testing-library/react";
import { Avatar } from "@/components/ui/Avatar";

test("Avatar without name renders fallback instead of crashing", () => {
  render(<Avatar />);
  expect(screen.getByRole("img", { name: "Unknown user" })).toHaveTextContent(
    "?",
  );
});
