/**
 * @file tests/unit/memorials/memorials.test.tsx
 * @brief Memorial helpers, API paths and MemorialHeader.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

const put = vi.fn().mockResolvedValue({});
const post = vi.fn().mockResolvedValue({});
vi.mock("@/lib/api/client", () => ({
  apiPut: (...a: unknown[]) => put(...a),
  apiPost: (...a: unknown[]) => post(...a),
  seg: (s: string) => encodeURIComponent(s),
}));

import { lifespan } from "@/lib/memorial";
import {
  memorializeUser,
  setPassedOn,
  unmemorializeUser,
} from "@/lib/api/memorials";
import { MemorialHeader } from "@/components/memorials/MemorialHeader";
import { useModals } from "@/stores/modals";
import { celebrationTitle } from "@/lib/celebrations";

describe("lifespan", () => {
  it("formats years", () => {
    expect(lifespan("1931-05-01", "2026-03-03")).toBe("1931 – 2026");
    expect(lifespan("--05-01", "2026-03-03")).toBe("Passed 2026");
    expect(lifespan("1931-05-01", null)).toBe("1931");
    expect(lifespan(null, null)).toBe("");
  });
});

describe("memorial API client paths", () => {
  beforeEach(() => {
    put.mockClear();
    post.mockClear();
  });
  it("all start with /api/v1/", async () => {
    await setPassedOn("m1", "2026-03-03");
    await memorializeUser("u1", null);
    await unmemorializeUser("u1");
    expect(put.mock.calls[0][0]).toBe("/api/v1/household/m1/passed-on");
    expect(put.mock.calls[0][1]).toEqual({ passed_on: "2026-03-03" });
    expect(post.mock.calls[0][0]).toBe("/api/v1/admin/users/u1/memorialize");
    expect(post.mock.calls[1][0]).toBe("/api/v1/admin/users/u1/unmemorialize");
    for (const c of [...put.mock.calls, ...post.mock.calls])
      expect(String(c[0]).startsWith("/api/v1/")).toBe(true);
  });
});

describe("MemorialHeader", () => {
  it("shows years and opens the composer with the @handle", () => {
    const show = vi.spyOn(useModals.getState(), "show");
    useModals.setState({ show });
    render(
      <MemorialHeader
        name="Ruth"
        handle="ruth"
        born="1931-05-01"
        passedOn="2026-03-03"
      />,
    );
    expect(screen.getByText("1931 – 2026")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Share a memory" }));
    expect(show).toHaveBeenCalledWith("create-post", { text: "@ruth " });
  });
  it("has no message or nudge buttons", () => {
    render(<MemorialHeader name="Ruth" handle={null} />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("celebrationTitle", () => {
  it("uses Remembering for remembrance", () => {
    expect(
      celebrationTitle({
        date: "2026-12-02",
        occasion: "remembrance",
        subject_type: "user",
        subject_id: "x",
        name: "Ruth",
        is_pet: false,
        link: "/app/u/ruth",
      }),
    ).toBe("Remembering Ruth");
  });
});
