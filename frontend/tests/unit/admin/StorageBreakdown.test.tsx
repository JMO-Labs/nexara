/**
 * @file tests/unit/admin/StorageBreakdown.test.tsx
 * @brief Category rows show byte counts and percentages.
 */
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StorageBreakdown } from "@/components/admin/StorageBreakdown";

const GB = 1024 ** 3;

describe("StorageBreakdown", () => {
  it("shows bytes and percent per category", () => {
    render(
      <StorageBreakdown
        categories={{ images: GB, videos: GB / 2, db: GB / 2 }}
      />,
    );
    const img = screen.getByText("Images").closest("li")!;
    expect(within(img).getByText("1.0 GB")).toBeInTheDocument();
    expect(within(img).getByText("50.0%")).toBeInTheDocument();
    const db = screen.getByText("Database").closest("li")!;
    expect(within(db).getByText("512.0 MB")).toBeInTheDocument();
    expect(within(db).getByText("25.0%")).toBeInTheDocument();
  });
});
