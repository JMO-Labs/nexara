/**
 * @file tests/unit/home/Greeting.test.tsx
 * @brief Greeting: day-part salutation, first name, date line.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Greeting } from "@/components/home/Greeting";

afterEach(() => vi.useRealTimers());

describe("Greeting", () => {
  it("says good evening at 19:00 with first name and date", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 19, 19, 0));
    render(<Greeting name="Ana Lopez" />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Good evening, Ana" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Thursday, November 19")).toBeInTheDocument();
  });

  it("says good morning at 08:00", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 19, 8, 0));
    render(<Greeting name="Ana" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Good morning, Ana",
    );
  });
});
