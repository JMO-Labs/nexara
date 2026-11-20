/**
 * @file tests/unit/kudos/KudosWall.test.tsx
 * @brief KudosWall: grid, empty state, subgroup filter, sort, load more.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";

const listKudos = vi.fn();
vi.mock("@/lib/api/kudos", () => ({
  listKudos: (...a: unknown[]) => listKudos(...a),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [{ id: "g1", name: "Chess" }] }),
}));

import { KudosWall } from "@/components/feed/KudosWall";

const k = (id: string, name: string, at: string, sg: string | null = null) => ({
  id,
  recipient_id: id,
  message: `msg-${id}`,
  author_id: "a",
  subgroup_id: sg,
  created_at: at,
  recipient: { id, username: id, display_name: name, avatar_url: null },
});

function wrap(embedded = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      <QueryClientProvider client={qc}>
        <KudosWall embedded={embedded} />
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("KudosWall", () => {
  it("shows empty state", async () => {
    listKudos.mockResolvedValue({ kudos: [], pagination: { has_more: false } });
    wrap();
    expect(await screen.findByText("No kudos yet")).toBeInTheDocument();
  });

  it("shows the Kudos page title and a Send Kudos action", async () => {
    listKudos.mockResolvedValue({ kudos: [], pagination: { has_more: false } });
    wrap();
    expect(
      screen.getByRole("heading", { level: 1, name: "Kudos" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Send Kudos" }),
    ).toBeInTheDocument();
  });

  it("renders newest first, oldest on sort change, and paginates", async () => {
    listKudos
      .mockResolvedValueOnce({
        kudos: [
          k("a", "Ana", "2026-01-02T00:00:00Z"),
          k("b", "Bo", "2026-01-01T00:00:00Z", "g1"),
        ],
        pagination: { next_cursor: "c2", has_more: true },
      })
      .mockResolvedValueOnce({
        kudos: [k("c", "Cy", "2025-12-01T00:00:00Z")],
        pagination: { has_more: false },
      });
    wrap();
    const names = async () =>
      (await screen.findAllByRole("article")).map((a) => a.textContent);
    expect((await names())[0]).toMatch(/Ana/);
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Cy")).toBeInTheDocument();
    expect(listKudos).toHaveBeenLastCalledWith("c2");
    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
    await userEvent.click(screen.getByRole("radio", { name: "Oldest" }));
    expect((await names())[0]).toMatch(/Cy/);
    await userEvent.selectOptions(screen.getByLabelText("Group"), "g1");
    expect(await screen.findAllByRole("article")).toHaveLength(1);
  });

  it("embedded: no page header, single-column list, compact toolbar", async () => {
    listKudos.mockResolvedValue({
      kudos: [k("a", "Ana", "2026-01-02T00:00:00Z")],
      pagination: { has_more: false },
    });
    wrap(true);
    const article = await screen.findByRole("article");
    expect(
      screen.queryByRole("heading", { level: 1, name: "Kudos" }),
    ).toBeNull();
    const list = article.parentElement as HTMLElement;
    expect(list.className).toContain("flex-col");
    expect(list.className).not.toContain("grid");
    expect(
      screen.getByRole("button", { name: "Send Kudos" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Group")).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Oldest" })).toBeNull();
  });

  it("non-embedded keeps the multi-column grid", async () => {
    listKudos.mockResolvedValue({
      kudos: [k("a", "Ana", "2026-01-02T00:00:00Z")],
      pagination: { has_more: false },
    });
    wrap();
    const article = await screen.findByRole("article");
    expect((article.parentElement as HTMLElement).className).toContain("grid");
  });
});
