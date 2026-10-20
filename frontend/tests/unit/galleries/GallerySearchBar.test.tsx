/**
 * @file tests/unit/galleries/GallerySearchBar.test.tsx
 * @brief Search input debounces 300ms and refetches galleries.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GallerySearchBar } from "@/components/galleries/GallerySearchBar";

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("GallerySearchBar", () => {
  it("renders search input with placeholder", () => {
    const mockOnSearch = vi.fn();
    wrap(<GallerySearchBar onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText("Search galleries");
    expect(input).toBeInTheDocument();
  });

  it("debounces search 300ms before calling onSearch", async () => {
    vi.useFakeTimers();
    const mockOnSearch = vi.fn();
    wrap(<GallerySearchBar onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(
      "Search galleries",
    ) as HTMLInputElement;

    // Type in input
    fireEvent.change(input, { target: { value: "vacation" } });
    expect(mockOnSearch).not.toHaveBeenCalled();

    // Advance time by 299ms — should not fire
    vi.advanceTimersByTime(299);
    expect(mockOnSearch).not.toHaveBeenCalled();

    // Advance to 300ms — should fire
    vi.advanceTimersByTime(1);
    expect(mockOnSearch).toHaveBeenCalledWith("vacation");

    vi.useRealTimers();
  });

  it("cancels previous debounce if input changes", async () => {
    vi.useFakeTimers();
    const mockOnSearch = vi.fn();
    wrap(<GallerySearchBar onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(
      "Search galleries",
    ) as HTMLInputElement;

    fireEvent.change(input, { target: { value: "vacation" } });
    vi.advanceTimersByTime(100);

    // Change input before debounce fires
    fireEvent.change(input, { target: { value: "beach" } });
    vi.advanceTimersByTime(300);

    // Should only call once with 'beach', not 'vacation'
    expect(mockOnSearch).toHaveBeenCalledOnce();
    expect(mockOnSearch).toHaveBeenCalledWith("beach");

    vi.useRealTimers();
  });

  it("calls onSearch with empty string when cleared", async () => {
    vi.useFakeTimers();
    const mockOnSearch = vi.fn();
    wrap(<GallerySearchBar onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(
      "Search galleries",
    ) as HTMLInputElement;

    fireEvent.change(input, { target: { value: "vacation" } });
    vi.advanceTimersByTime(300);
    expect(mockOnSearch).toHaveBeenCalledWith("vacation");

    mockOnSearch.mockClear();
    fireEvent.change(input, { target: { value: "" } });
    vi.advanceTimersByTime(300);
    expect(mockOnSearch).toHaveBeenCalledWith("");

    vi.useRealTimers();
  });
});
