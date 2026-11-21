/**
 * @file tests/unit/ui/page/SearchField.test.tsx
 * @brief SearchField aria label, change, debounce.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { SearchField } from "@/components/ui/page";

afterEach(() => vi.useRealTimers());

describe("SearchField", () => {
  it("uses label as aria-label and calls onChange immediately by default", () => {
    const onChange = vi.fn();
    render(
      <SearchField
        value=""
        onChange={onChange}
        placeholder="Find"
        label="Search photos"
      />,
    );
    const input = screen.getByRole("searchbox", { name: "Search photos" });
    expect(input).toHaveAttribute("placeholder", "Find");
    fireEvent.change(input, { target: { value: "a" } });
    expect(onChange).toHaveBeenCalledWith("a");
  });
  it("debounces onChange", () => {
    vi.useFakeTimers();
    const onChange = vi.fn();
    render(
      <SearchField
        value=""
        onChange={onChange}
        placeholder="p"
        label="S"
        debounceMs={300}
      />,
    );
    const input = screen.getByRole("searchbox", { name: "S" });
    fireEvent.change(input, { target: { value: "ab" } });
    expect(input).toHaveValue("ab");
    expect(onChange).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("ab");
  });
  it("syncs when value prop changes", () => {
    const { rerender } = render(
      <SearchField value="a" onChange={() => {}} placeholder="p" label="S" />,
    );
    rerender(
      <SearchField value="b" onChange={() => {}} placeholder="p" label="S" />,
    );
    expect(screen.getByRole("searchbox")).toHaveValue("b");
  });
});
