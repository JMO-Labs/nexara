/**
 * @file tests/unit/settings/StorageTab.test.tsx
 * @brief StorageTab: quota display, breakdown, warning, layout, a11y.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { StorageTab } from "@/components/settings/StorageTab";
import * as hooks from "@/hooks/useStorage";
import { useSession } from "@/stores/session";

vi.mock("@/hooks/useStorage");

const GB = 1024 ** 3;
const usage = (used: number) => ({
  used_bytes: used * GB,
  quota_bytes: 10 * GB,
  by_type: {
    photos: 1 * GB,
    videos: 1 * GB,
    documents: 0.25 * GB,
    other: 0.25 * GB,
  },
});
const mockHook = (data: unknown, extra: object = {}) =>
  vi.mocked(hooks.useStorage).mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    ...extra,
  } as never);

describe("StorageTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSession.getState().setUser({ id: "u1" } as never);
  });

  it("shows used / quota in GB", () => {
    mockHook(usage(2.5));
    render(<StorageTab />);
    expect(screen.getByText("2.5 GB / 10 GB used")).toBeInTheDocument();
    expect(hooks.useStorage).toHaveBeenCalledWith("u1");
  });

  it.each([
    [5, "green"],
    [8, "yellow"],
    [9.5, "red"],
  ])("colors bar for %s GB as %s", (gb, tone) => {
    mockHook(usage(gb));
    render(<StorageTab />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", String(Math.round(gb * 10)));
    expect(bar.firstElementChild).toHaveAttribute("data-tone", tone);
  });

  it("renders breakdown as a table", () => {
    mockHook(usage(2.5));
    render(<StorageTab />);
    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
    for (const l of ["Photos", "Videos", "Documents", "Other"])
      expect(screen.getByRole("rowheader", { name: l })).toBeInTheDocument();
  });

  it("no warning at or below 80%", () => {
    mockHook(usage(8));
    render(<StorageTab />);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("warns above 80% with percentage text", () => {
    mockHook(usage(8.5));
    render(<StorageTab />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "You're using 85% of your storage quota. Consider deleting old media.",
    );
  });

  it("uses responsive stacked/side-by-side layout", () => {
    mockHook(usage(2.5));
    render(<StorageTab />);
    expect(screen.getByTestId("storage-layout").className).toMatch(
      /flex-col.*md:flex-row|grid-cols-1.*md:grid-cols-2/,
    );
  });

  it("makes table rows keyboard reachable", () => {
    mockHook(usage(2.5));
    render(<StorageTab />);
    screen
      .getAllByRole("row")
      .slice(1)
      .forEach((r) => expect(r).toHaveAttribute("tabindex", "0"));
  });

  it("shows loading and error states", () => {
    mockHook(undefined, { isLoading: true });
    const { unmount } = render(<StorageTab />);
    expect(screen.getByText(/loading storage/i)).toBeInTheDocument();
    unmount();
    mockHook(undefined, { isError: true });
    render(<StorageTab />);
    expect(screen.getByText(/could not load storage/i)).toBeInTheDocument();
  });
});
