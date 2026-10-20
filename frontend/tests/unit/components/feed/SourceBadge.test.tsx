/**
 * @file tests/unit/components/feed/SourceBadge.test.tsx
 * @brief Unit tests for SourceBadge component.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SourceBadge } from "@/components/feed/SourceBadge";

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    onClick,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: (e: React.MouseEvent) => void;
    [key: string]: unknown;
  }) => (
    <a href={href} onClick={onClick} {...rest}>
      {children}
    </a>
  ),
}));

describe("SourceBadge", () => {
  it("renders Community pill when subgroupId is null", () => {
    render(<SourceBadge subgroupId={null} subgroupName={null} />);
    expect(screen.getByText("Community")).toBeInTheDocument();
    expect(screen.getByLabelText("Posted in Community")).toBeInTheDocument();
  });

  it("renders named subgroup pill when subgroupId is set", () => {
    render(
      <SourceBadge
        subgroupId="sg-123"
        subgroupName="Book Club"
        subgroupSlug="book-club"
      />,
    );
    expect(screen.getByText("Book Club")).toBeInTheDocument();
    expect(screen.getByLabelText("Posted in Book Club")).toBeInTheDocument();
  });

  it("links to subgroup slug when provided", () => {
    render(
      <SourceBadge
        subgroupId="sg-123"
        subgroupName="Book Club"
        subgroupSlug="book-club"
      />,
    );
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("/app/subgroups/book-club");
  });

  it("renders non-clickable span (no anchor) when subgroupId set but slug absent", () => {
    render(<SourceBadge subgroupId="sg-123" subgroupName="Book Club" />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByLabelText("Posted in Book Club")).toBeInTheDocument();
  });

  it("click does not bubble to parent", () => {
    const parentClick = vi.fn();
    render(
      <div onClick={parentClick}>
        <SourceBadge
          subgroupId="sg-123"
          subgroupName="Book Club"
          subgroupSlug="book-club"
        />
      </div>,
    );
    const link = screen.getByRole("link");
    fireEvent.click(link);
    expect(parentClick).not.toHaveBeenCalled();
  });
});
