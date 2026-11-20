/**
 * @file tests/unit/admin/AdminGate.test.tsx
 * @brief AdminGate: renders children for admins only.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AdminGate } from "@/components/admin/AdminGate";
import { useSession } from "@/stores/session";

const user = (role: string) => ({ id: "u1", role }) as never;

describe("AdminGate", () => {
  beforeEach(() => useSession.setState({ user: null, status: "idle" }));

  it("blocks unauthenticated viewers", () => {
    render(
      <AdminGate>
        <p>secret</p>
      </AdminGate>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      /admin access required/i,
    );
    expect(screen.queryByText("secret")).toBeNull();
  });

  it("blocks non-admin members", () => {
    useSession.setState({ user: user("member") });
    render(
      <AdminGate>
        <p>secret</p>
      </AdminGate>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/member/);
    expect(screen.queryByText("secret")).toBeNull();
  });

  it("renders children for admins", () => {
    useSession.setState({ user: user("admin") });
    render(
      <AdminGate>
        <p>secret</p>
      </AdminGate>,
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
