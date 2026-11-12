/**
 * @file tests/unit/home/WelcomeBanner.test.tsx
 * @brief WelcomeBanner: greeting, first-name extraction, dayPart.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { WelcomeBanner, dayPart } from "@/components/home/WelcomeBanner";

afterEach(() => vi.useRealTimers());

describe("dayPart", () => {
  it.each([
    [new Date(2026, 10, 10, 9), "Tuesday morning"],
    [new Date(2026, 10, 10, 14), "Tuesday afternoon"],
    [new Date(2026, 10, 10, 20), "Tuesday evening"],
  ])("%s", (d, expected) => {
    expect(dayPart(d)).toBe(expected);
  });
});

describe("WelcomeBanner", () => {
  it("greets by first name in an h1 with day-part line", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 10, 20));
    renderWithProviders(<WelcomeBanner userName="Ada Lovelace" />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Hi Ada." }),
    ).toBeInTheDocument();
    expect(screen.getByText("Tuesday evening")).toBeInTheDocument();
  });

  it("falls back to 'there' for a blank name", () => {
    renderWithProviders(<WelcomeBanner userName="   " />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Hi there." }),
    ).toBeInTheDocument();
  });
});
